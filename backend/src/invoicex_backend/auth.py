"""Authentication boundary for fixed demo accounts and completed Privy users."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, Request, status

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import LoginRole
from invoicex_backend.onboarding_models import CompanyType, OnboardingStatus
from invoicex_backend.privy_auth import verify_privy_access_token


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    role: LoginRole
    email: str
    source: Literal["DEMO", "MEMBER", "PRIVY"] = "DEMO"
    privy_user_id: str | None = None
    company_id: str | None = None
    company_name: str | None = None
    wallet_address: str | None = None


def issue_access_token(
    identity: AuthenticatedIdentity,
    settings: BackendSettings,
) -> tuple[str, str]:
    expires_at = int(time.time()) + settings.auth_token_ttl_seconds
    payload = {
        "email": identity.email,
        "exp": expires_at,
        "role": identity.role.value,
        "source": identity.source,
    }
    body = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _sign(body, settings.auth_token_secret)
    return f"{body}.{signature}", datetime.fromtimestamp(expires_at, UTC).isoformat()


async def require_authenticated_identity(request: Request) -> AuthenticatedIdentity | None:
    existing = getattr(request.state, "authenticated_identity", None)
    if isinstance(existing, AuthenticatedIdentity):
        return existing
    settings: BackendSettings = request.app.state.settings
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        if not settings.api_auth_required:
            return None
        raise _unauthorized()
    if token.count(".") == 2:
        identity = _privy_identity(request, token, settings)
        request.state.authenticated_identity = identity
        return identity
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(_sign(body, settings.auth_token_secret), signature):
            raise ValueError("signature")
        payload = json.loads(_decode(body))
        if not isinstance(payload, dict) or int(payload["exp"]) < int(time.time()):
            raise ValueError("expired")
        role = LoginRole(str(payload["role"]))
        email = str(payload["email"])
        # Tokens issued before member authentication was added did not carry a
        # source.  Preserve their fixed-demo behavior while making new MEMBER
        # tokens resolve the completed company account.
        source = str(payload.get("source", "DEMO"))
        if source == "MEMBER":
            identity = _member_identity(request, role=role, email=email)
        elif source == "DEMO":
            identity = AuthenticatedIdentity(role=role, email=email, source="DEMO")
        else:
            raise ValueError("unsupported authentication source")
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

    async def dependency(request: Request) -> AuthenticatedIdentity | None:
        identity = await require_authenticated_identity(request)
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


def _privy_identity(
    request: Request,
    token: str,
    settings: BackendSettings,
) -> AuthenticatedIdentity:
    principal = verify_privy_access_token(token, settings)
    repository = request.app.state.invoice_service.repository
    user = repository.get_onboarding_user(principal.user_id)
    if (
        user is None
        or user.onboarding_status is not OnboardingStatus.COMPLETED
        or user.company_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="InvoiceX 회원가입을 완료한 후 이용해 주세요.",
        )
    company = repository.get_company(user.company_id)
    wallet = repository.get_company_wallet(user.company_id)
    if company is None or wallet is None or wallet.privy_user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="가입한 회사와 Embedded Wallet 연결을 확인할 수 없습니다.",
        )
    role = {
        CompanyType.SUPPLIER: LoginRole.SUPPLIER,
        CompanyType.BUYER: LoginRole.BUYER,
        CompanyType.INVESTOR: LoginRole.INVESTOR,
    }[company.type]
    settlement_wallet = repository.get_company_settlement_wallet(company.id)
    return AuthenticatedIdentity(
        role=role,
        email=user.email,
        source="PRIVY",
        privy_user_id=principal.user_id,
        company_id=company.id,
        company_name=company.name,
        wallet_address=settlement_wallet[1] if settlement_wallet is not None else wallet.address,
    )


def _member_identity(
    request: Request,
    *,
    role: LoginRole,
    email: str,
) -> AuthenticatedIdentity:
    """Resolve an InvoiceX password session to its completed company account.

    A member token intentionally contains only the role and email.  Business
    routes still need the same company scope and public settlement address as
    a Privy session, otherwise a completed supplier cannot access or issue an
    RWA for its own invoice after a password login.
    """

    onboarding = request.app.state.onboarding_service
    profile = onboarding.auth_me_for_email(email)
    user = profile.user
    if (
        profile.onboarding_status is not OnboardingStatus.COMPLETED
        or profile.company is None
        or profile.embedded_wallet is None
        or user.company_id is None
    ):
        raise _unauthorized()
    if profile.company.type != CompanyType(role.value.upper()):
        raise _unauthorized()
    settlement_wallet = onboarding.settlement_wallet_for_email(email)
    return AuthenticatedIdentity(
        role=role,
        email=user.email,
        source="MEMBER",
        privy_user_id=user.privy_user_id,
        company_id=profile.company.id,
        company_name=profile.company.name,
        wallet_address=settlement_wallet.address,
    )


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
