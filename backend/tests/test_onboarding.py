from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from invoicex_backend.errors import OnboardingApiError
from invoicex_backend.onboarding import OnboardingService
from invoicex_backend.privy_users import HttpPrivyUserGateway, PrivyWalletRecord
from invoicex_backend.repository import SQLiteRwaRepository

from .conftest import mock_settings


@dataclass
class FakePrivyGateway:
    fail_wallet_attempts: int = 0
    wallet_calls: list[tuple[str, str]] = field(default_factory=list)

    async def verified_email(self, user_id: str) -> str:
        return f"{user_id.rsplit(':', 1)[-1]}@example.com"

    async def get_or_create_solana_wallet(
        self, user_id: str, *, idempotency_key: str
    ) -> PrivyWalletRecord:
        self.wallet_calls.append((user_id, idempotency_key))
        if self.fail_wallet_attempts > 0:
            self.fail_wallet_attempts -= 1
            raise OnboardingApiError(
                502,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "Wallet provisioning failed.",
            )
        suffix = user_id.rsplit(":", 1)[-1]
        return PrivyWalletRecord(
            id=f"privy-wallet-{suffix}",
            address="7YpT1nGKM4gL4pWj6Rc2sN9u8TqfAEHvkM3dXeZbQ5Uc",
            user_id=user_id,
        )

    async def aclose(self) -> None:
        return None


@contextmanager
def onboarding_client(
    tmp_path: Path, gateway: FakePrivyGateway
) -> Iterator[tuple[TestClient, ec.EllipticCurvePrivateKey, SQLiteRwaRepository]]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    settings = mock_settings(
        tmp_path / "uploads",
        PRIVY_APP_ID="test-privy-app",
        PRIVY_APP_SECRET="test-secret",
        PRIVY_VERIFICATION_KEY=public_key.public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode(),
    )
    repository = SQLiteRwaRepository(tmp_path / "onboarding.sqlite3")
    service = OnboardingService(repository, gateway)
    app = create_app(settings=settings, onboarding_service=service)
    with TestClient(app) as client:
        yield client, private_key, repository
    repository.close()


def token(private_key: ec.EllipticCurvePrivateKey, user_id: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user_id,
            "sid": f"session-{user_id}",
            "iss": "privy.io",
            "aud": "test-privy-app",
            "iat": now,
            "exp": now + 3600,
        },
        private_key,
        algorithm="ES256",
    )


def headers(private_key: ec.EllipticCurvePrivateKey, user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(private_key, user_id)}"}


def company_payload(company_type: str = "SUPPLIER", business_number: str = "123-45-67890"):
    return {
        "company": {
            "name": "에이씨미 주식회사",
            "type": company_type,
            "businessRegistrationNumber": business_number,
        },
        "representative": {
            "name": "홍길동",
            "title": "재무팀 매니저",
            "phone": "010-0000-0000",
        },
    }


def test_auth_me_creates_a_pending_user_from_privy(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        response = client.get(
            "/api/v1/auth/me", headers=headers(private_key, "did:privy:user-one")
        )

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": response.json()["user"]["id"],
            "privyUserId": "did:privy:user-one",
            "email": "user-one@example.com",
            "name": None,
            "title": None,
            "phone": None,
            "companyId": None,
            "onboardingStatus": "NEEDS_COMPANY_PROFILE",
        },
        "company": None,
        "embeddedWallet": None,
        "onboardingStatus": "NEEDS_COMPANY_PROFILE",
        "nextPath": "/signup",
    }


def test_supplier_onboarding_creates_a_user_owned_wallet(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        response = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:supplier"),
            json=company_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["onboardingStatus"] == "COMPLETED"
    assert body["nextPath"] == "/supplier"
    assert body["embeddedWallet"]["privyUserId"] == "did:privy:supplier"
    assert body["company"]["businessRegistrationNumber"] == "123-45-67890"
    assert body["company"]["kybStatus"] == "NOT_PERFORMED"
    assert body["logicalVault"] is None
    assert gateway.wallet_calls[0][0] == "did:privy:supplier"


def test_investor_onboarding_creates_only_a_logical_vault_row(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        response = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:investor"),
            json=company_payload("INVESTOR"),
        )

    assert response.status_code == 200
    assert response.json()["nextPath"] == "/investor"
    assert response.json()["logicalVault"]["availableUsdc"] == 0


def test_wallet_failure_keeps_company_and_rotates_retry_key(tmp_path: Path) -> None:
    gateway = FakePrivyGateway(fail_wallet_attempts=1)
    with onboarding_client(tmp_path, gateway) as (client, private_key, repository):
        auth_headers = headers(private_key, "did:privy:retry-user")
        first = client.post(
            "/api/v1/onboarding/company", headers=auth_headers, json=company_payload()
        )
        pending = client.get("/api/v1/auth/me", headers=auth_headers)
        second = client.post(
            "/api/v1/onboarding/company", headers=auth_headers, json=company_payload()
        )
        stored = repository.get_onboarding_user("did:privy:retry-user")

    assert first.status_code == 502
    assert first.json()["code"] == "EMBEDDED_WALLET_PROVISIONING_FAILED"
    assert pending.json()["onboardingStatus"] == "PROVISIONING_EMBEDDED_WALLET"
    assert second.status_code == 200
    assert len(gateway.wallet_calls) == 2
    assert gateway.wallet_calls[0][1] != gateway.wallet_calls[1][1]
    assert stored is not None and stored.onboarding_status.value == "COMPLETED"


def test_wallet_retry_survives_a_backend_restart(tmp_path: Path) -> None:
    failed_gateway = FakePrivyGateway(fail_wallet_attempts=1)
    with onboarding_client(tmp_path, failed_gateway) as (client, private_key, _):
        first = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:restart-user"),
            json=company_payload(),
        )

    resumed_gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, resumed_gateway) as (client, private_key, _):
        resumed = client.get(
            "/api/v1/auth/me",
            headers=headers(private_key, "did:privy:restart-user"),
        )
        completed = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:restart-user"),
            json=company_payload(),
        )

    assert first.status_code == 502
    assert resumed.json()["onboardingStatus"] == "PROVISIONING_EMBEDDED_WALLET"
    assert completed.status_code == 200
    assert completed.json()["onboardingStatus"] == "COMPLETED"
    assert len(resumed_gateway.wallet_calls) == 1


def test_business_number_and_completed_user_cannot_be_reused(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        first_headers = headers(private_key, "did:privy:first")
        second_headers = headers(private_key, "did:privy:second")
        first = client.post(
            "/api/v1/onboarding/company", headers=first_headers, json=company_payload()
        )
        repeated = client.post(
            "/api/v1/onboarding/company", headers=first_headers, json=company_payload()
        )
        duplicate = client.post(
            "/api/v1/onboarding/company", headers=second_headers, json=company_payload()
        )

    assert first.status_code == 200
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "ONBOARDING_ALREADY_COMPLETED"
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "BUSINESS_REGISTRATION_ALREADY_USED"


def test_onboarding_requires_a_privy_access_token(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, _, _):
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "PRIVY_TOKEN_INVALID"


@pytest.mark.asyncio
async def test_privy_wallet_request_assigns_the_privy_user_as_owner(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(
            201,
            json={
                "id": "wallet-1",
                "address": "7YpT1nGKM4gL4pWj6Rc2sN9u8TqfAEHvkM3dXeZbQ5Uc",
                "chain_type": "solana",
                "owner_id": None,
            },
        )

    settings = mock_settings(
        tmp_path / "uploads",
        PRIVY_APP_ID="test-privy-app",
        PRIVY_APP_SECRET="test-secret",
        PRIVY_API_BASE_URL="https://api.privy.test",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = HttpPrivyUserGateway(settings, http_client=client)

    wallet = await gateway.get_or_create_solana_wallet(
        "did:privy:user-owner",
        idempotency_key="onboarding-attempt-1",
    )
    await client.aclose()

    assert wallet.user_id == "did:privy:user-owner"
    assert len(requests) == 2
    lookup_request = requests[0]
    assert lookup_request.url.params["user_id"] == "did:privy:user-owner"
    assert lookup_request.url.params["chain_type"] == "solana"
    create_request = requests[1]
    assert create_request.headers["privy-idempotency-key"] == "onboarding-attempt-1"
    assert create_request.headers["privy-app-id"] == "test-privy-app"
    assert create_request.url.path == "/v1/wallets"
    assert create_request.method == "POST"
    assert create_request.headers["content-type"].startswith("application/json")
    payload = json.loads(create_request.content)
    assert payload["chain_type"] == "solana"
    assert "entity" not in payload
    assert payload["owner"] == {"user_id": "did:privy:user-owner"}
