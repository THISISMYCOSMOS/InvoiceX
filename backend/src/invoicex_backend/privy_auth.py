"""Privy access-token verification for the onboarding API only."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any, cast

import jwt
from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import OnboardingApiError

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class PrivyPrincipal:
    user_id: str
    session_id: str


def _unauthorized(message: str) -> OnboardingApiError:
    return OnboardingApiError(status.HTTP_401_UNAUTHORIZED, "PRIVY_TOKEN_INVALID", message)


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
    if settings.privy_verification_key:
        return _verification_key(settings.privy_verification_key)
    raise OnboardingApiError(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "PRIVY_CONFIGURATION_MISSING",
        "Privy 인증 설정이 완료되지 않았습니다.",
    )


async def require_privy_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> PrivyPrincipal:
    settings = cast(BackendSettings, request.app.state.settings)
    if not settings.privy_app_id:
        raise OnboardingApiError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PRIVY_CONFIGURATION_MISSING",
            "Privy 인증 설정이 완료되지 않았습니다.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Privy access token이 필요합니다.")
    try:
        payload = jwt.decode(
            credentials.credentials,
            key=_signing_key(credentials.credentials, settings),
            algorithms=["ES256"],
            audience=settings.privy_app_id,
            issuer="privy.io",
            options={"require": ["sub", "sid", "iss", "aud", "iat", "exp"]},
        )
    except OnboardingApiError:
        raise
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise _unauthorized("Privy access token이 유효하지 않거나 만료되었습니다.") from exc
    return PrivyPrincipal(
        user_id=str(payload["sub"]),
        session_id=str(payload["sid"]),
    )


PrivyPrincipalDependency = Annotated[PrivyPrincipal, Depends(require_privy_principal)]
