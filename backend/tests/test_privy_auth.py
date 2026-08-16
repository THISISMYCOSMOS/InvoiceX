from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from solders.pubkey import Pubkey

from invoicex_backend import auth as auth_module
from invoicex_backend.app import create_app
from invoicex_backend.config import BackendSettings

APP_ID = "invoice-x-test-app"
PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_KEY = PRIVATE_KEY.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def _token_pair(
    wallet_address: str | None,
    *,
    access_user_id: str = "did:privy:test-user",
    identity_user_id: str | None = None,
    expired: bool = False,
    wallet_client_type: str = "privy",
) -> dict[str, str]:
    now = datetime.now(UTC)
    expires_at = now - timedelta(minutes=1) if expired else now + timedelta(minutes=30)
    common = {
        "iss": "privy.io",
        "aud": APP_ID,
        "iat": int((now - timedelta(seconds=1)).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    linked_accounts: list[dict[str, object]] = [
        {"type": "email", "address": "investor@example.com"},
    ]
    if wallet_address is not None:
        linked_accounts.append(
            {
                "type": "wallet",
                "address": wallet_address,
                "chain_type": "solana",
                "wallet_client_type": wallet_client_type,
            }
        )
    access_token = jwt.encode(
        {**common, "sub": access_user_id, "sid": "session-test"},
        PRIVATE_KEY,
        algorithm="ES256",
    )
    identity_token = jwt.encode(
        {
            **common,
            "sub": identity_user_id or access_user_id,
            "linked_accounts": json.dumps(linked_accounts),
        },
        PRIVATE_KEY,
        algorithm="ES256",
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "privy-id-token": identity_token,
    }


def _auth_client(tmp_path: Path, **overrides: object) -> TestClient:
    values: dict[str, object] = {
        "AUTH_MODE": "privy",
        "PRIVY_APP_ID": APP_ID,
        "PRIVY_VERIFICATION_KEY": PUBLIC_KEY,
    }
    values.update(overrides)
    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="mock",
        SOLANA_MODE="mock",
        UPLOAD_DIRECTORY=tmp_path / "uploads",
        RWA_DATABASE_PATH=tmp_path / "invoicex-rwa.sqlite3",
        PUBLIC_BASE_URL="http://testserver",
        **values,
    )
    return TestClient(create_app(settings=settings))


def test_privy_mode_rejects_an_unauthenticated_investor_request(tmp_path: Path) -> None:
    with _auth_client(tmp_path) as client:
        response = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": str(Pubkey.new_unique())},
        )

    assert response.status_code == 401
    assert response.json()["message"] == "Privy access token이 필요합니다."


def test_privy_mode_allows_the_users_linked_embedded_solana_wallet(tmp_path: Path) -> None:
    wallet_address = str(Pubkey.new_unique())
    with _auth_client(tmp_path) as client:
        response = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": wallet_address},
            headers=_token_pair(wallet_address),
        )

    assert response.status_code == 200
    assert response.json()["ownerWalletAddress"] == wallet_address


def test_privy_mode_can_resolve_a_rotating_key_from_jwks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeJwksClient:
        @staticmethod
        def get_signing_key_from_jwt(_: str) -> object:
            return type("SigningKey", (), {"key": PRIVATE_KEY.public_key()})()

    monkeypatch.setattr(auth_module, "_jwks_client", lambda _: FakeJwksClient())
    wallet_address = str(Pubkey.new_unique())
    with _auth_client(
        tmp_path,
        PRIVY_VERIFICATION_KEY=None,
        PRIVY_JWKS_URL="https://auth.privy.io/test/jwks.json",
    ) as client:
        response = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": wallet_address},
            headers=_token_pair(wallet_address),
        )

    assert response.status_code == 200


def test_privy_mode_rejects_a_different_wallet(tmp_path: Path) -> None:
    linked_wallet = str(Pubkey.new_unique())
    requested_wallet = str(Pubkey.new_unique())
    with _auth_client(tmp_path) as client:
        response = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": requested_wallet},
            headers=_token_pair(linked_wallet),
        )

    assert response.status_code == 403
    assert "현재 Privy 사용자의" in response.json()["message"]


def test_privy_mode_does_not_treat_an_external_wallet_as_embedded(tmp_path: Path) -> None:
    wallet_address = str(Pubkey.new_unique())
    with _auth_client(tmp_path) as client:
        response = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": wallet_address},
            headers=_token_pair(wallet_address, wallet_client_type="phantom"),
        )

    assert response.status_code == 403


def test_privy_mode_rejects_mismatched_or_expired_tokens(tmp_path: Path) -> None:
    wallet_address = str(Pubkey.new_unique())
    with _auth_client(tmp_path) as client:
        mismatched = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": wallet_address},
            headers=_token_pair(wallet_address, identity_user_id="did:privy:other-user"),
        )
        expired = client.get(
            "/api/v1/investor/vault",
            params={"ownerWalletAddress": wallet_address},
            headers=_token_pair(wallet_address, expired=True),
        )

    assert mismatched.status_code == 401
    assert "사용자가 일치하지 않습니다" in mismatched.json()["message"]
    assert expired.status_code == 401
    assert "유효하지 않거나 만료" in expired.json()["message"]


def test_privy_dashboard_requires_an_embedded_solana_wallet(tmp_path: Path) -> None:
    with _auth_client(tmp_path) as client:
        response = client.get(
            "/api/v1/investor/dashboard",
            headers=_token_pair(None),
        )

    assert response.status_code == 403
    assert "연결된 Solana 임베디드 지갑" in response.json()["message"]
