from __future__ import annotations

import hashlib
import json
import sqlite3
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
from solders.keypair import Keypair

from invoicex_backend.app import create_app
from invoicex_backend.errors import OnboardingApiError
from invoicex_backend.onboarding import OnboardingService
from invoicex_backend.privy_users import HttpPrivyUserGateway, PrivyWalletRecord
from invoicex_backend.repository import SQLiteRwaRepository

from .conftest import mock_settings


@dataclass
class FakePrivyGateway:
    fail_wallet_attempts: int = 0
    emails: dict[str, str] = field(default_factory=dict)
    wallet_calls: list[tuple[str, str]] = field(default_factory=list)
    verified_wallets: list[tuple[str, str]] = field(default_factory=list)
    deleted_user_ids: list[str] = field(default_factory=list)

    async def verified_email(self, user_id: str) -> str:
        return self.emails.get(user_id, f"{user_id.rsplit(':', 1)[-1]}@example.com")

    async def delete_user(self, user_id: str) -> None:
        self.deleted_user_ids.append(user_id)

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
            address=str(Keypair.from_seed(hashlib.sha256(user_id.encode()).digest()).pubkey()),
            user_id=user_id,
        )

    async def verify_solana_wallet(
        self, user_id: str, address: str
    ) -> PrivyWalletRecord:
        self.verified_wallets.append((user_id, address))
        return PrivyWalletRecord(
            id=f"client-wallet-{address[:8]}",
            address=address,
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


def token(
    private_key: ec.EllipticCurvePrivateKey,
    user_id: str,
    *,
    issued_at_offset_seconds: int = 0,
) -> str:
    now = int(time.time()) + issued_at_offset_seconds
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


def company_payload(
    company_type: str = "SUPPLIER",
    registration_number: str = "123-45-67890",
    country_code: str = "KR",
):
    return {
        "password": "member-password-123",
        "company": {
            "name": "에이씨미 주식회사",
            "type": company_type,
            "countryCode": country_code,
            "registrationNumber": registration_number,
        },
        "representative": {
            "name": "홍길동",
            "title": "재무팀 매니저",
            "phone": "010-0000-0000",
        },
    }


@contextmanager
def privy_business_client(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, ec.EllipticCurvePrivateKey]]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    settings = mock_settings(
        tmp_path / "uploads",
        API_AUTH_REQUIRED=True,
        AUTH_TOKEN_SECRET="test-token-secret-that-is-long-enough-for-hmac",
        PRIVY_APP_ID="test-privy-app",
        PRIVY_APP_SECRET="test-secret",
        PRIVY_VERIFICATION_KEY=public_key.public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode(),
    )
    app = create_app(settings=settings)
    app.state.onboarding_service = OnboardingService(
        app.state.invoice_service.repository,
        FakePrivyGateway(),
        vault_initializer=app.state.invoice_service.provision_investor_vault,
    )
    with TestClient(app) as client:
        yield client, private_key


def register_company(
    client: TestClient,
    private_key: ec.EllipticCurvePrivateKey,
    *,
    user_id: str,
    company_type: str,
    company_name: str,
    business_number: str,
) -> dict[str, object]:
    payload = company_payload(
        company_type,
        business_number,
        "KR" if company_type == "SUPPLIER" else "US",
    )
    payload["company"]["name"] = company_name
    response = client.post(
        "/api/v1/onboarding/company",
        headers=headers(private_key, user_id),
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


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
    assert body["company"]["countryCode"] == "KR"
    assert body["company"]["registrationNumber"] == "1234567890"
    assert body["company"]["kybStatus"] == "NOT_PERFORMED"
    assert body["logicalVault"] is None
    assert gateway.wallet_calls[0][0] == "did:privy:supplier"


def test_onboarding_links_the_client_created_solana_wallet(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    user_id = "did:privy:client-wallet"
    wallet_address = str(Keypair().pubkey())
    payload = company_payload()
    payload["embeddedWalletAddress"] = wallet_address

    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        response = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, user_id),
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["embeddedWallet"]["address"] == wallet_address
    assert gateway.verified_wallets == [(user_id, wallet_address)]
    assert gateway.wallet_calls == []


def test_completed_account_can_replace_an_unusable_server_wallet(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    user_id = "did:privy:wallet-repair"
    replacement_address = str(Keypair().pubkey())

    with onboarding_client(tmp_path, gateway) as (client, private_key, repository):
        account_headers = headers(private_key, user_id)
        created = client.post(
            "/api/v1/onboarding/company",
            headers=account_headers,
            json=company_payload(
                company_type="INVESTOR",
                registration_number="12-3456789",
                country_code="US",
            ),
        )
        old_address = created.json()["embeddedWallet"]["address"]
        repaired = client.put(
            "/api/v1/auth/embedded-wallet",
            headers=account_headers,
            json={"address": replacement_address},
        )
        company_id = repaired.json()["company"]["id"]
        saved_wallet = repository.get_company_wallet(company_id)

    assert repaired.status_code == 200
    assert replacement_address != old_address
    assert repaired.json()["embeddedWallet"]["address"] == replacement_address
    assert saved_wallet is not None
    assert saved_wallet.address == replacement_address


def test_completed_investor_can_restore_a_missing_wallet_and_vault(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    user_id = "did:privy:wallet-restore"
    replacement_address = str(Keypair().pubkey())

    with onboarding_client(tmp_path, gateway) as (client, private_key, repository):
        account_headers = headers(private_key, user_id)
        created = client.post(
            "/api/v1/onboarding/company",
            headers=account_headers,
            json=company_payload(
                company_type="INVESTOR",
                registration_number="12-3456789",
                country_code="US",
            ),
        )
        company_id = created.json()["company"]["id"]
        with repository._connection:
            repository._connection.execute(
                "DELETE FROM wallets WHERE company_id = ?", (company_id,)
            )
            repository._connection.execute(
                "DELETE FROM company_vaults WHERE investor_company_id = ?", (company_id,)
            )

        repaired = client.put(
            "/api/v1/auth/embedded-wallet",
            headers=account_headers,
            json={"address": replacement_address},
        )

        saved_wallet = repository.get_company_wallet(company_id)
        saved_vault = repository.get_company_vault(company_id)

    assert repaired.status_code == 200
    assert repaired.json()["embeddedWallet"]["address"] == replacement_address
    assert saved_wallet is not None
    assert saved_wallet.address == replacement_address
    assert saved_vault is not None


def test_completed_supplier_can_update_company_profile(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    profile_headers: dict[str, str]
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        profile_headers = headers(private_key, "did:privy:profile-update")
        created = client.post(
            "/api/v1/onboarding/company",
            headers=profile_headers,
            json=company_payload(),
        )
        assert created.status_code == 200
        payload = company_payload(registration_number="987-65-43210")
        payload.pop("password")
        payload["company"]["name"] = "InvoiceX Demo Supplier"
        payload["representative"] = {
            "name": "황순익",
            "title": "대표이사",
            "phone": "010-9876-5432",
        }
        updated = client.put(
            "/api/v1/auth/company-profile",
            headers=profile_headers,
            json=payload,
        )
        loaded = client.get("/api/v1/auth/me", headers=profile_headers)

    assert updated.status_code == 200
    assert updated.json()["company"]["name"] == "InvoiceX Demo Supplier"
    assert updated.json()["company"]["registrationNumber"] == "9876543210"
    assert updated.json()["user"]["name"] == "황순익"
    assert updated.json()["user"]["title"] == "대표이사"
    assert updated.json()["user"]["phone"] == "010-9876-5432"
    assert loaded.status_code == 200
    assert loaded.json()["company"] == updated.json()["company"]
    assert loaded.json()["user"]["name"] == "황순익"


def test_company_profile_update_keeps_role_and_country_immutable(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        profile_headers = headers(private_key, "did:privy:profile-identity")
        created = client.post(
            "/api/v1/onboarding/company",
            headers=profile_headers,
            json=company_payload(),
        )
        assert created.status_code == 200
        foreign_payload = company_payload(
            company_type="BUYER",
            country_code="US",
            registration_number="12-3456789",
        )
        foreign_payload.pop("password")
        response = client.put(
            "/api/v1/auth/company-profile",
            headers=profile_headers,
            json=foreign_payload,
        )

    assert response.status_code == 422
    assert response.json()["code"] == "COMPANY_IDENTITY_IMMUTABLE"


def test_completed_member_can_log_in_with_the_signup_password(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, repository):
        onboarding = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:password-member"),
            json=company_payload(),
        )
        assert onboarding.status_code == 200

        saved_hash = repository.get_user_password_hash(
            "did:privy:password-member"
        )
        assert saved_hash is not None
        assert saved_hash.startswith("scrypt$")
        assert saved_hash != "member-password-123"

        login = client.post(
            "/api/v1/auth/login",
            json={
                "role": "Supplier",
                "email": "password-member@example.com",
                "password": "member-password-123",
            },
        )
        rejected = client.post(
            "/api/v1/auth/login",
            json={
                "role": "Supplier",
                "email": "password-member@example.com",
                "password": "incorrect-password",
            },
        )

        assert login.status_code == 200
        assert login.json()["authMode"] == "MEMBER"
        profile = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login.json()['accessToken']}"},
        )

    assert rejected.status_code == 401
    assert profile.status_code == 200
    assert profile.json()["onboardingStatus"] == "COMPLETED"


def test_member_can_switch_between_embedded_and_external_settlement_wallets(
    tmp_path: Path,
) -> None:
    gateway = FakePrivyGateway()
    user_id = "did:privy:wallet-switcher"
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        onboarding = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, user_id),
            json=company_payload(),
        )
        assert onboarding.status_code == 200

        default_wallet = client.get(
            "/api/v1/auth/settlement-wallet", headers=headers(private_key, user_id)
        )
        external_address = str(Keypair().pubkey())
        external_wallet = client.put(
            "/api/v1/auth/settlement-wallet",
            headers=headers(private_key, user_id),
            json={"walletType": "EXTERNAL", "address": external_address},
        )
        restored_wallet = client.put(
            "/api/v1/auth/settlement-wallet",
            headers=headers(private_key, user_id),
            json={"walletType": "EMBEDDED"},
        )

    assert default_wallet.status_code == 200
    assert default_wallet.json()["walletType"] == "EMBEDDED"
    assert external_wallet.status_code == 200
    assert external_wallet.json()["walletType"] == "EXTERNAL"
    assert external_wallet.json()["address"] == external_address
    assert restored_wallet.status_code == 200
    assert restored_wallet.json()["walletType"] == "EMBEDDED"
    assert restored_wallet.json()["address"] == default_wallet.json()["address"]


def test_investor_onboarding_provisions_a_vault_and_allows_a_mock_deposit(
    tmp_path: Path,
) -> None:
    user_id = "did:privy:investor-vault"
    with privy_business_client(tmp_path) as (client, private_key):
        onboarding = register_company(
            client,
            private_key,
            user_id=user_id,
            company_type="INVESTOR",
            company_name="Vault Capital",
            business_number="12-3456789",
        )
        wallet_address = onboarding["embeddedWallet"]["address"]
        account_headers = headers(private_key, user_id)

        vault = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": wallet_address},
            headers=account_headers,
        )
        prepared = client.post(
            "/api/v1/investor/vault/deposits/prepare",
            headers=account_headers,
            json={"ownerWalletAddress": wallet_address, "amountUsdc": 25},
        )
        confirmed = client.post(
            "/api/v1/investor/vault/deposits/confirm",
            headers=account_headers,
            json={
                "ownerWalletAddress": wallet_address,
                "amountUsdc": 25,
                "signature": "mock-investor-onboarding-deposit",
            },
        )

    assert vault.status_code == 200
    assert vault.json()["availableUsdc"] == 0
    assert prepared.status_code == 200
    assert prepared.json()["provider"] == "MOCK"
    assert confirmed.status_code == 200
    assert confirmed.json()["availableUsdc"] == 25


def test_account_withdrawal_disables_password_login_and_wallet_access(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    user_id = "did:privy:account-withdrawal"
    with onboarding_client(tmp_path, gateway) as (client, private_key, repository):
        onboarding = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, user_id),
            json=company_payload(),
        )
        assert onboarding.status_code == 200
        company_id = onboarding.json()["company"]["id"]

        withdrawal = client.delete(
            "/api/v1/auth/account",
            headers=headers(private_key, user_id),
        )
        password_login = client.post(
            "/api/v1/auth/login",
            json={
                "role": "Supplier",
                "email": "account-withdrawal@example.com",
                "password": "member-password-123",
            },
        )
        user = repository.get_onboarding_user(user_id)
        password_hash = repository.get_user_password_hash(user_id)
        company = repository.get_company(company_id)
        wallet = repository.get_company_wallet(company_id)
        wallet_access = client.get(
            "/api/v1/auth/settlement-wallet", headers=headers(private_key, user_id)
        )

    assert withdrawal.status_code == 200
    assert withdrawal.json()["onboardingStatus"] == "WITHDRAWN"
    assert password_login.status_code == 401
    assert wallet_access.status_code == 403
    assert user is None
    assert password_hash is None
    assert company is None
    assert wallet is None
    assert gateway.deleted_user_ids == [user_id]


def test_account_withdrawal_allows_rejoining_with_the_same_company(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    user_id = "did:privy:account-rejoin"
    rejoined_user_id = "did:privy:account-rejoin-new"
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        first_onboarding = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, user_id),
            json=company_payload(),
        )
        assert first_onboarding.status_code == 200

        withdrawal = client.delete(
            "/api/v1/auth/account",
            headers=headers(private_key, user_id),
        )
        rejoin = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, rejoined_user_id),
            json=company_payload(),
        )

    assert withdrawal.status_code == 200
    assert rejoin.status_code == 200
    assert rejoin.json()["onboardingStatus"] == "COMPLETED"
    assert rejoin.json()["embeddedWallet"]["address"] != first_onboarding.json()["embeddedWallet"]["address"]
    assert len(gateway.wallet_calls) == 2
    assert gateway.deleted_user_ids == [user_id]


def test_new_onboarding_requires_a_password(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        payload = company_payload()
        payload.pop("password")
        response = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:missing-password"),
            json=payload,
        )

    assert response.status_code == 422
    assert response.json()["code"] == "PASSWORD_REQUIRED"


def test_korean_company_registration_number_requires_ten_digits(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        response = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:invalid-business-number"),
            json=company_payload(registration_number="123-45-6789"),
        )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_buyer_can_register_with_us_ein_but_supplier_cannot(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        buyer = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:us-buyer"),
            json=company_payload(
                company_type="BUYER",
                country_code="US",
                registration_number="12-3456789",
            ),
        )
        supplier = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:us-supplier"),
            json=company_payload(
                country_code="US",
                registration_number="98-7654321",
            ),
        )
        invalid_ein = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:invalid-ein"),
            json=company_payload(
                company_type="INVESTOR",
                country_code="US",
                registration_number="12-345678",
            ),
        )

    assert buyer.status_code == 200
    assert buyer.json()["company"]["countryCode"] == "US"
    assert buyer.json()["company"]["registrationNumber"] == "123456789"
    assert supplier.status_code == 422
    assert invalid_ein.status_code == 422


def test_privy_business_requests_use_database_company_role_and_scope(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    with privy_business_client(tmp_path) as (client, private_key):
        supplier = register_company(
            client,
            private_key,
            user_id="did:privy:supplier-one",
            company_type="SUPPLIER",
            company_name="Supplier One",
            business_number="111-11-11111",
        )
        buyer = register_company(
            client,
            private_key,
            user_id="did:privy:buyer-one",
            company_type="BUYER",
            company_name="Prime Mobility",
            business_number="22-2222222",
        )
        other_supplier = register_company(
            client,
            private_key,
            user_id="did:privy:supplier-two",
            company_type="SUPPLIER",
            company_name="Supplier Two",
            business_number="333-33-33333",
        )
        register_company(
            client,
            private_key,
            user_id="did:privy:buyer-two",
            company_type="BUYER",
            company_name="Other Buyer",
            business_number="44-4444444",
        )

        supplier_headers = headers(private_key, "did:privy:supplier-one")
        created = client.post(
            "/api/v1/invoices",
            headers=supplier_headers,
            files=contract_files,
        )
        assert created.status_code == 201
        invoice = created.json()["invoice"]
        invoice_id = invoice["id"]
        assert invoice["supplier"] == {
            "id": supplier["company"]["id"],
            "name": "Supplier One",
            "walletAddress": supplier["embeddedWallet"]["address"],
            "vaultAddress": None,
        }
        assert invoice["buyer"]["id"] == buyer["company"]["id"]

        assert len(client.get(
            "/api/v1/invoices",
            headers=headers(private_key, "did:privy:buyer-one"),
        ).json()["items"]) == 1
        assert client.get(
            f"/api/v1/invoices/{invoice_id}",
            headers=headers(private_key, "did:privy:supplier-two"),
        ).status_code == 404
        assert other_supplier["company"]["id"] != supplier["company"]["id"]

        requested = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request",
            headers=supplier_headers,
        )
        assert requested.status_code == 200
        assert len(client.get(
            "/api/v1/verifications",
            headers=headers(private_key, "did:privy:buyer-one"),
        ).json()["items"]) == 1
        assert client.get(
            "/api/v1/verifications",
            headers=headers(private_key, "did:privy:buyer-two"),
        ).json()["items"] == []
        assert client.get(
            "/api/v1/investor/dashboard",
            headers=supplier_headers,
        ).status_code == 403


def test_password_member_uses_its_saved_settlement_wallet_for_rwa_issuance(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    """A password session must retain company scope without a fresh Privy OTP."""

    with privy_business_client(tmp_path) as (client, private_key):
        supplier = register_company(
            client,
            private_key,
            user_id="did:privy:password-supplier",
            company_type="SUPPLIER",
            company_name="Password Supplier",
            business_number="111-11-11111",
        )
        buyer = register_company(
            client,
            private_key,
            user_id="did:privy:password-buyer",
            company_type="BUYER",
            company_name="Prime Mobility",
            business_number="22-2222222",
        )
        supplier_headers = headers(private_key, "did:privy:password-supplier")
        buyer_headers = headers(private_key, "did:privy:password-buyer")
        settlement_wallet = str(Keypair().pubkey())
        updated_wallet = client.put(
            "/api/v1/auth/settlement-wallet",
            headers=supplier_headers,
            json={"walletType": "EXTERNAL", "address": settlement_wallet},
        )
        assert updated_wallet.status_code == 200

        created = client.post(
            "/api/v1/invoices", headers=supplier_headers, files=contract_files
        )
        assert created.status_code == 201
        invoice_id = created.json()["invoice"]["id"]
        requested = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request",
            headers=supplier_headers,
        )
        assert requested.status_code == 200
        confirmed = client.post(
            f"/api/v1/verifications/{requested.json()['invoice']['verificationId']}/confirm",
            headers=buyer_headers,
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["invoice"]["status"] == "OFFER_READY"

        # Simulate a legacy invoice that still has demo identity data.
        stored_invoice = client.app.state.invoice_service._invoice(invoice_id)
        stored_invoice.supplier = stored_invoice.supplier.model_copy(
            update={
                "id": "SUPPLIER_ALPHA",
                "wallet_address": "DEMO_SUPPLIER_WALLET",
            }
        )
        client.app.state.invoice_service._save_invoice(stored_invoice)

        password_login = client.post(
            "/api/v1/auth/login",
            json={
                "role": "Supplier",
                "email": "password-supplier@example.com",
                "password": "member-password-123",
            },
        )
        assert password_login.status_code == 200
        member_headers = {
            "Authorization": f"Bearer {password_login.json()['accessToken']}"
        }
        listed = client.get("/api/v1/invoices", headers=member_headers)
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [invoice_id]

        issued = client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            headers=member_headers,
            json={"response": "ACCEPT"},
        )

    assert supplier["company"]["id"] == created.json()["invoice"]["supplier"]["id"]
    assert buyer["company"]["id"] == confirmed.json()["invoice"]["buyer"]["id"]
    assert issued.status_code == 200
    assert issued.json()["invoice"]["status"] == "RWA_ISSUED"
    assert issued.json()["invoice"]["supplier"]["walletAddress"] == settlement_wallet


def test_privy_business_api_rejects_incomplete_onboarding(tmp_path: Path) -> None:
    with privy_business_client(tmp_path) as (client, private_key):
        pending_headers = headers(private_key, "did:privy:pending-business-user")
        assert client.get("/api/v1/auth/me", headers=pending_headers).status_code == 200
        blocked = client.get("/api/v1/invoices", headers=pending_headers)

    assert blocked.status_code == 403
    assert "회원가입을 완료" in str(blocked.json())


def test_investor_onboarding_creates_only_a_logical_vault_row(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        response = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:investor"),
            json=company_payload(
                "INVESTOR",
                registration_number="12-3456789",
                country_code="US",
            ),
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


def test_country_and_registration_number_pair_and_completed_user_cannot_be_reused(
    tmp_path: Path,
) -> None:
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
        foreign_payload = company_payload(
            company_type="BUYER",
            country_code="US",
            registration_number="12-3456789",
        )
        foreign_payload["representative"]["phone"] = "+1 212-555-0100"
        different_country = client.post(
            "/api/v1/onboarding/company",
            headers=headers(private_key, "did:privy:third"),
            json=foreign_payload,
        )

    assert first.status_code == 200
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "ONBOARDING_ALREADY_COMPLETED"
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "COMPANY_REGISTRATION_ALREADY_USED"
    assert different_country.status_code == 200


def test_local_sqlite_migrates_the_legacy_company_identifier(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company_type TEXT NOT NULL,
            business_registration_number TEXT NOT NULL UNIQUE,
            kyb_status TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO companies VALUES (
            'legacy-company', 'Legacy Supplier', 'SUPPLIER',
            '123-45-67890', 'NOT_PERFORMED', 'ACTIVE'
        )
        """
    )
    connection.commit()
    connection.close()

    repository = SQLiteRwaRepository(database_path)
    company = repository.get_company("legacy-company")
    repository.close()

    assert company is not None
    assert company.country_code == "KR"
    assert company.registration_number == "1234567890"


def test_same_email_cannot_create_two_local_accounts(tmp_path: Path) -> None:
    shared_email = "Finance@Example.com"
    gateway = FakePrivyGateway(
        emails={
            "did:privy:first-email": shared_email,
            "did:privy:second-email": shared_email.lower(),
        }
    )
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        first = client.get(
            "/api/v1/auth/me",
            headers=headers(private_key, "did:privy:first-email"),
        )
        duplicate = client.get(
            "/api/v1/auth/me",
            headers=headers(private_key, "did:privy:second-email"),
        )

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_onboarding_requires_a_privy_access_token(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, _, _):
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "PRIVY_TOKEN_INVALID"


def test_privy_access_token_allows_small_clock_skew(tmp_path: Path) -> None:
    gateway = FakePrivyGateway()
    with onboarding_client(tmp_path, gateway) as (client, private_key, _):
        future_token = token(
            private_key,
            "did:privy:clock-skew",
            issued_at_offset_seconds=5,
        )
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {future_token}"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_privy_wallet_request_assigns_the_privy_user_as_owner(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    user_id = "did:privy:user-owner"
    external_id = HttpPrivyUserGateway._wallet_external_id(user_id)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path == "/v1/wallets":
            return httpx.Response(200, json={"data": []})
        if request.method == "GET" and request.url.path == "/v1/wallets/wallet-1":
            return httpx.Response(
                200,
                json={
                    "id": "wallet-1",
                    "address": "7YpT1nGKM4gL4pWj6Rc2sN9u8TqfAEHvkM3dXeZbQ5Uc",
                    "chain_type": "solana",
                    "external_id": external_id,
                    "owner_id": "key-quorum-1",
                    "entity": None,
                },
            )
        if (
            request.method == "POST"
            and request.url.path == "/v1/users/wallet/address"
        ):
            assert json.loads(request.content) == {
                "address": "7YpT1nGKM4gL4pWj6Rc2sN9u8TqfAEHvkM3dXeZbQ5Uc"
            }
            return httpx.Response(200, json={"id": user_id, "linked_accounts": []})
        return httpx.Response(
            201,
            json={
                "id": "wallet-1",
                "address": "7YpT1nGKM4gL4pWj6Rc2sN9u8TqfAEHvkM3dXeZbQ5Uc",
                "chain_type": "solana",
                "owner_id": "key-quorum-1",
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
        user_id,
        idempotency_key="onboarding-attempt-1",
    )
    await client.aclose()

    assert wallet.user_id == user_id
    assert len(requests) == 4
    lookup_request = requests[0]
    assert lookup_request.url.params["user_id"] == user_id
    assert lookup_request.url.params["chain_type"] == "solana"
    assert lookup_request.url.params["external_id"] == external_id
    create_request = requests[1]
    assert create_request.headers["privy-idempotency-key"] == "onboarding-attempt-1"
    assert create_request.headers["privy-app-id"] == "test-privy-app"
    assert create_request.url.path == "/v1/wallets"
    assert create_request.method == "POST"
    assert create_request.headers["content-type"].startswith("application/json")
    payload = json.loads(create_request.content)
    assert payload["chain_type"] == "solana"
    assert payload["external_id"] == external_id
    assert "entity" not in payload
    assert payload["owner"] == {"user_id": user_id}
    detail_request = requests[2]
    assert detail_request.method == "GET"
    assert detail_request.url.path == "/v1/wallets/wallet-1"
    owner_lookup_request = requests[3]
    assert owner_lookup_request.method == "POST"
    assert owner_lookup_request.url.path == "/v1/users/wallet/address"


@pytest.mark.asyncio
async def test_privy_gateway_verifies_a_client_embedded_wallet_owner(tmp_path: Path) -> None:
    user_id = "did:privy:client-wallet-owner"
    address = str(Keypair().pubkey())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/users/wallet/address"
        assert json.loads(request.content) == {"address": address}
        return httpx.Response(
            200,
            json={
                "id": user_id,
                "linked_accounts": [
                    {
                        "id": "client-wallet-id",
                        "type": "wallet",
                        "chain_type": "solana",
                        "wallet_client_type": "privy",
                        "address": address,
                    }
                ],
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

    wallet = await gateway.verify_solana_wallet(user_id, address)
    await client.aclose()

    assert wallet == PrivyWalletRecord(
        id="client-wallet-id",
        address=address,
        user_id=user_id,
    )


@pytest.mark.asyncio
async def test_privy_user_deletion_calls_the_delete_user_api(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    user_id = "did:privy:user-delete"

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    settings = mock_settings(
        tmp_path / "uploads",
        PRIVY_APP_ID="test-privy-app",
        PRIVY_APP_SECRET="test-secret",
        PRIVY_API_BASE_URL="https://api.privy.test",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = HttpPrivyUserGateway(settings, http_client=client)

    await gateway.delete_user(user_id)
    await client.aclose()

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "DELETE"
    assert request.url.path == f"/v1/users/{user_id}"
    assert request.headers["privy-app-id"] == "test-privy-app"


@pytest.mark.asyncio
async def test_privy_wallet_lookup_selects_only_the_invoicex_wallet(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    user_id = "did:privy:wallet-choice"
    external_id = HttpPrivyUserGateway._wallet_external_id(user_id)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/wallets/invoicex-wallet":
            return httpx.Response(
                200,
                json={
                    "id": "invoicex-wallet",
                    "address": "InvoiceXSolanaAddress",
                    "chain_type": "solana",
                    "external_id": external_id,
                    "entity": {"id": user_id, "type": "user"},
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "unrelated-wallet",
                        "address": "UnrelatedSolanaAddress",
                        "chain_type": "solana",
                        "external_id": "another_product_wallet",
                        "entity": {"id": user_id, "type": "user"},
                    },
                    {
                        "id": "invoicex-wallet",
                        "address": "InvoiceXSolanaAddress",
                        "chain_type": "solana",
                        "external_id": external_id,
                        "entity": {"id": user_id, "type": "user"},
                    },
                ]
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
        user_id,
        idempotency_key="unused-for-existing-wallet",
    )
    await client.aclose()

    assert wallet.id == "invoicex-wallet"
    assert wallet.address == "InvoiceXSolanaAddress"
    assert len(requests) == 2
    assert requests[0].method == "GET"
    assert requests[1].url.path == "/v1/wallets/invoicex-wallet"


def test_buyer_registered_after_invoice_creation_receives_matching_requests(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    with privy_business_client(tmp_path) as (client, private_key):
        register_company(
            client,
            private_key,
            user_id="did:privy:late-supplier",
            company_type="SUPPLIER",
            company_name="Late Supplier",
            business_number="55-555-55555",
        )
        created = client.post(
            "/api/v1/invoices",
            headers=headers(private_key, "did:privy:late-supplier"),
            files=contract_files,
        )
        assert created.status_code == 201
        assert created.json()["invoice"]["buyer"]["id"] == "BUYER_PRIME"
        assert created.json()["invoice"]["buyer"]["name"] == "Prime Mobility"

        buyer = register_company(
            client,
            private_key,
            user_id="did:privy:late-buyer",
            company_type="BUYER",
            company_name="Prime Mobility",
            business_number="66-6666666",
        )
        listed = client.get(
            "/api/v1/invoices",
            headers=headers(private_key, "did:privy:late-buyer"),
        )

        assert listed.status_code == 200
        assert len(listed.json()["items"]) == 1
        assert listed.json()["items"][0]["buyer"]["id"] == buyer["company"]["id"]
