"""Privy session and embedded-wallet ownership verification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any, cast

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from invoicex_backend.config import BackendSettings

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class PrivyPrincipal:
    """Verified Privy user data needed by InvoiceX authorization checks."""

    user_id: str
    session_id: str
    email: str | None
    embedded_solana_wallets: frozenset[str]

    def require_embedded_wallet(self, wallet_address: str) -> None:
        if wallet_address not in self.embedded_solana_wallets:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="요청한 지갑은 현재 Privy 사용자의 Solana 임베디드 지갑이 아닙니다.",
            )

    def primary_embedded_wallet(self) -> str:
        if not self.embedded_solana_wallets:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="현재 Privy 사용자에게 연결된 Solana 임베디드 지갑이 없습니다.",
            )
        return sorted(self.embedded_solana_wallets)[0]


def _settings(request: Request) -> BackendSettings:
    return cast(BackendSettings, request.app.state.backend_settings)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _verification_key(raw_key: str) -> Any:
    normalized = raw_key.strip().replace("\\n", "\n")
    if normalized.startswith("{"):
        return jwt.PyJWK.from_json(normalized).key
    return normalized


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=300)


def _signing_key(token: str, settings: BackendSettings) -> Any:
    if settings.privy_jwks_url:
        return _jwks_client(settings.privy_jwks_url).get_signing_key_from_jwt(token).key
    assert settings.privy_verification_key is not None
    return _verification_key(settings.privy_verification_key)


def _decode_token(
    token: str,
    settings: BackendSettings,
    *,
    required_claims: list[str],
) -> dict[str, Any]:
    assert settings.privy_app_id is not None
    try:
        payload = jwt.decode(
            token,
            key=_signing_key(token, settings),
            algorithms=["ES256"],
            audience=settings.privy_app_id,
            issuer="privy.io",
            options={"require": required_claims},
        )
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise _unauthorized("Privy 인증 토큰이 유효하지 않거나 만료되었습니다.") from exc
    return cast(dict[str, Any], payload)


def _linked_accounts(identity_payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_accounts = identity_payload.get("linked_accounts")
    if isinstance(raw_accounts, str):
        try:
            raw_accounts = json.loads(raw_accounts)
        except json.JSONDecodeError as exc:
            raise _unauthorized(
                "Privy identity token의 연결 계정 정보가 올바르지 않습니다."
            ) from exc
    if not isinstance(raw_accounts, list):
        raise _unauthorized("Privy identity token에 연결 계정 정보가 없습니다.")
    return [account for account in raw_accounts if isinstance(account, dict)]


async def require_privy_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    identity_token: Annotated[str | None, Header(alias="privy-id-token")] = None,
) -> PrivyPrincipal | None:
    """Verify both Privy auth and identity tokens when authentication is enabled."""

    settings = _settings(request)
    if settings.auth_mode == "disabled":
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Privy access token이 필요합니다.")
    if not identity_token:
        raise _unauthorized("Privy identity token이 필요합니다.")

    access_payload = _decode_token(
        credentials.credentials,
        settings,
        required_claims=["sub", "sid", "iss", "aud", "iat", "exp"],
    )
    identity_payload = _decode_token(
        identity_token,
        settings,
        required_claims=["sub", "linked_accounts", "iss", "aud", "iat", "exp"],
    )
    user_id = str(access_payload["sub"])
    if identity_payload["sub"] != user_id:
        raise _unauthorized("Privy access token과 identity token의 사용자가 일치하지 않습니다.")

    email: str | None = None
    wallets: set[str] = set()
    for account in _linked_accounts(identity_payload):
        account_type = account.get("type")
        address = account.get("address")
        if account_type == "email" and isinstance(address, str):
            email = address
        if (
            account_type == "wallet"
            and isinstance(address, str)
            and (account.get("chain_type") or account.get("chainType")) == "solana"
            and (account.get("wallet_client_type") or account.get("walletClientType")) == "privy"
        ):
            wallets.add(address)

    return PrivyPrincipal(
        user_id=user_id,
        session_id=str(access_payload["sid"]),
        email=email,
        embedded_solana_wallets=frozenset(wallets),
    )


PrivyPrincipalDependency = Annotated[PrivyPrincipal | None, Depends(require_privy_principal)]


def require_wallet_owner(principal: PrivyPrincipal | None, wallet_address: str) -> None:
    """Enforce ownership in Privy mode while leaving explicit local mock mode usable."""

    if principal is not None:
        principal.require_embedded_wallet(wallet_address)
