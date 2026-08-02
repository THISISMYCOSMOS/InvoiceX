"""Small signed-token auth boundary for the fixed InvoiceX demo accounts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import LoginRole


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    role: LoginRole
    email: str


def issue_access_token(
    identity: AuthenticatedIdentity,
    settings: BackendSettings,
) -> tuple[str, str]:
    expires_at = int(time.time()) + settings.auth_token_ttl_seconds
    payload = {
        "email": identity.email,
        "exp": expires_at,
        "role": identity.role.value,
    }
    body = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _sign(body, settings.auth_token_secret)
    return f"{body}.{signature}", datetime.fromtimestamp(expires_at, UTC).isoformat()


def require_authenticated_identity(request: Request) -> AuthenticatedIdentity | None:
    settings: BackendSettings = request.app.state.settings
    if not settings.api_auth_required:
        return None
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized()
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(_sign(body, settings.auth_token_secret), signature):
            raise ValueError("signature")
        payload = json.loads(_decode(body))
        if not isinstance(payload, dict) or int(payload["exp"]) < int(time.time()):
            raise ValueError("expired")
        identity = AuthenticatedIdentity(
            role=LoginRole(str(payload["role"])),
            email=str(payload["email"]),
        )
        request.state.authenticated_identity = identity
        return identity
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise _unauthorized() from None


def require_roles(*allowed_roles: LoginRole) -> Callable[[Request], AuthenticatedIdentity | None]:
    """Return a dependency that restricts GCP demo API actions by role.

    Local mock mode deliberately keeps the API open, preserving the existing
    browser-only demo and contract tests. Once API authentication is enabled,
    a valid token must additionally belong to one of the explicitly permitted
    fixed demo roles.
    """

    allowed = frozenset(allowed_roles)

    def dependency(request: Request) -> AuthenticatedIdentity | None:
        identity = require_authenticated_identity(request)
        if identity is None:
            return None
        if identity.role not in allowed:
            names = ", ".join(role.value for role in sorted(allowed, key=lambda role: role.value))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {names}.",
            )
        return identity

    return dependency


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode("utf-8")


def _sign(body: str, secret: str) -> str:
    return _encode(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid InvoiceX demo access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
