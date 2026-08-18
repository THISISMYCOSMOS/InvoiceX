"""Company signup orchestration with retry-safe Privy wallet provisioning."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import status

from invoicex_backend.errors import OnboardingApiError
from invoicex_backend.onboarding_models import (
    AuthMeResponse,
    Company,
    CompanyType,
    CompanyWallet,
    LogicalVault,
    OnboardCompanyRequest,
    OnboardingResponse,
    OnboardingStatus,
    OnboardingUser,
    next_path,
)
from invoicex_backend.privy_auth import PrivyPrincipal
from invoicex_backend.privy_users import PrivyUserGateway
from invoicex_backend.repository import RwaRepository


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class OnboardingService:
    def __init__(self, repository: RwaRepository, privy: PrivyUserGateway) -> None:
        self._repository = repository
        self._privy = privy
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def _lock_for(self, user_id: str) -> asyncio.Lock:
        async with self._locks_guard:
            return self._locks.setdefault(user_id, asyncio.Lock())

    async def auth_me(self, principal: PrivyPrincipal) -> AuthMeResponse:
        user = await self._ensure_user(principal.user_id)
        company = self._company_for(user)
        wallet = self._wallet_for(user)
        return AuthMeResponse(
            user=user,
            company=company,
            embedded_wallet=wallet,
            onboarding_status=user.onboarding_status,
            next_path=next_path(company, user.onboarding_status),
        )

    async def onboard_company(
        self,
        principal: PrivyPrincipal,
        payload: OnboardCompanyRequest,
    ) -> OnboardingResponse:
        lock = await self._lock_for(principal.user_id)
        async with lock:
            user = await self._ensure_user(principal.user_id)
            if user.onboarding_status is OnboardingStatus.COMPLETED:
                raise OnboardingApiError(
                    status.HTTP_409_CONFLICT,
                    "ONBOARDING_ALREADY_COMPLETED",
                    "이미 가입이 완료된 Privy 사용자입니다.",
                )

            company = self._company_for(user) or Company(
                id=_id("cmp"),
                name=payload.company.name,
                type=payload.company.type,
                business_registration_number=payload.company.business_registration_number,
            )
            user = user.model_copy(
                update={
                    "name": payload.representative.name,
                    "title": payload.representative.title,
                    "phone": payload.representative.phone,
                    "company_id": company.id,
                    "onboarding_status": OnboardingStatus.PROVISIONING_EMBEDDED_WALLET,
                    "wallet_idempotency_key": (
                        user.wallet_idempotency_key or f"onboarding_{uuid.uuid4().hex}"
                    ),
                }
            )
            user, company = self._repository.save_company_profile(user, company)
            idempotency_key = user.wallet_idempotency_key
            if not idempotency_key:
                raise OnboardingApiError(
                    status.HTTP_409_CONFLICT,
                    "ONBOARDING_STATE_INVALID",
                    "Wallet 생성 재시도 정보를 찾을 수 없습니다.",
                )
            try:
                privy_wallet = await self._privy.get_or_create_solana_wallet(
                    principal.user_id,
                    idempotency_key=idempotency_key,
                )
            except OnboardingApiError:
                self._repository.rotate_wallet_idempotency_key(
                    principal.user_id, f"onboarding_{uuid.uuid4().hex}"
                )
                raise

            wallet = CompanyWallet(
                id=_id("wal"),
                company_id=company.id,
                privy_user_id=principal.user_id,
                privy_wallet_id=privy_wallet.id,
                address=privy_wallet.address,
            )
            vault = (
                LogicalVault(id=_id("vlt"), investor_company_id=company.id)
                if company.type is CompanyType.INVESTOR
                else None
            )
            user = self._repository.complete_onboarding(
                principal.user_id,
                wallet,
                vault,
            )
            saved_wallet = self._repository.get_company_wallet(company.id)
            saved_vault = self._repository.get_company_vault(company.id)
            if saved_wallet is None:
                raise OnboardingApiError(
                    status.HTTP_409_CONFLICT,
                    "ONBOARDING_STATE_INVALID",
                    "저장된 Embedded Wallet을 찾을 수 없습니다.",
                )
            return OnboardingResponse(
                user=user,
                company=company,
                embedded_wallet=saved_wallet,
                logical_vault=saved_vault,
                onboarding_status=user.onboarding_status,
                next_path=next_path(company, user.onboarding_status),
            )

    async def _ensure_user(self, privy_user_id: str) -> OnboardingUser:
        existing = self._repository.get_onboarding_user(privy_user_id)
        if existing is not None:
            return existing
        email = await self._privy.verified_email(privy_user_id)
        return self._repository.ensure_onboarding_user(
            OnboardingUser(
                id=_id("usr"),
                privy_user_id=privy_user_id,
                email=email,
                onboarding_status=OnboardingStatus.NEEDS_COMPANY_PROFILE,
            )
        )

    def _company_for(self, user: OnboardingUser) -> Company | None:
        return self._repository.get_company(user.company_id) if user.company_id else None

    def _wallet_for(self, user: OnboardingUser) -> CompanyWallet | None:
        return self._repository.get_company_wallet(user.company_id) if user.company_id else None

    async def aclose(self) -> None:
        await self._privy.aclose()
