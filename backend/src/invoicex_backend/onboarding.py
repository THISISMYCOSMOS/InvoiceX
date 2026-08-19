"""Company signup orchestration with retry-safe Privy wallet provisioning."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import status
from solders.pubkey import Pubkey

from invoicex_backend.errors import OnboardingApiError
from invoicex_backend.models import LoginRole
from invoicex_backend.onboarding_models import (
    AuthMeResponse,
    Company,
    CompanyType,
    CompanyWallet,
    DeleteAccountResponse,
    LogicalVault,
    OnboardCompanyRequest,
    OnboardingResponse,
    OnboardingStatus,
    OnboardingUser,
    SettlementWallet,
    UpdateCompanyProfileRequest,
    UpdateSettlementWalletRequest,
    next_path,
)
from invoicex_backend.privy_auth import PrivyPrincipal
from invoicex_backend.privy_users import PrivyUserGateway
from invoicex_backend.passwords import hash_password, verify_password
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

    def auth_me_for_email(self, email: str) -> AuthMeResponse:
        user = self._repository.get_onboarding_user_by_email(email)
        if user is None:
            raise OnboardingApiError(
                status.HTTP_401_UNAUTHORIZED,
                "MEMBER_SESSION_INVALID",
                "로그인 사용자 정보를 찾을 수 없습니다.",
            )
        company = self._company_for(user)
        wallet = self._wallet_for(user)
        return AuthMeResponse(
            user=user,
            company=company,
            embedded_wallet=wallet,
            onboarding_status=user.onboarding_status,
            next_path=next_path(company, user.onboarding_status),
        )

    def update_company_profile(
        self, email: str, payload: UpdateCompanyProfileRequest
    ) -> AuthMeResponse:
        user = self._repository.get_onboarding_user_by_email(email)
        if (
            user is None
            or user.company_id is None
            or user.onboarding_status is not OnboardingStatus.COMPLETED
        ):
            raise OnboardingApiError(
                status.HTTP_401_UNAUTHORIZED,
                "MEMBER_SESSION_INVALID",
                "로그인 사용자 정보를 찾을 수 없습니다.",
            )
        company = self._repository.get_company(user.company_id)
        if company is None:
            raise OnboardingApiError(
                status.HTTP_409_CONFLICT,
                "COMPANY_PROFILE_NOT_FOUND",
                "수정할 기업 정보를 찾을 수 없습니다.",
            )
        if (
            payload.company.type != company.type
            or payload.company.country_code != company.country_code
        ):
            raise OnboardingApiError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "COMPANY_IDENTITY_IMMUTABLE",
                "국가 코드와 계정 역할은 변경할 수 없습니다.",
            )
        updated_user = user.model_copy(
            update={
                "name": payload.representative.name,
                "title": payload.representative.title,
                "phone": payload.representative.phone,
            }
        )
        updated_company = company.model_copy(
            update={
                "name": payload.company.name,
                "registration_number": payload.company.registration_number,
            }
        )
        self._repository.update_company_profile(updated_user, updated_company)
        return self.auth_me_for_email(email)

    def authenticate_password_login(
        self, email: str, password: str, role: LoginRole
    ) -> OnboardingUser | None:
        user = self._repository.get_onboarding_user_by_email(email)
        if user is None or user.onboarding_status is not OnboardingStatus.COMPLETED:
            return None
        company = self._company_for(user)
        password_hash = self._repository.get_user_password_hash(user.privy_user_id)
        if (
            company is None
            or company.type != CompanyType(role.value.upper())
            or password_hash is None
            or not verify_password(password, password_hash)
        ):
            return None
        return user

    def settlement_wallet_for_email(self, email: str) -> SettlementWallet:
        user = self._repository.get_onboarding_user_by_email(email)
        if (
            user is None
            or user.company_id is None
            or user.onboarding_status is not OnboardingStatus.COMPLETED
        ):
            raise OnboardingApiError(
                status.HTTP_401_UNAUTHORIZED,
                "MEMBER_SESSION_INVALID",
                "로그인 사용자 정보를 찾을 수 없습니다.",
            )
        embedded_wallet = self._repository.get_company_wallet(user.company_id)
        if embedded_wallet is None:
            raise OnboardingApiError(
                status.HTTP_409_CONFLICT,
                "WALLET_NOT_AVAILABLE",
                "가입한 Embedded Wallet을 찾을 수 없습니다.",
            )
        selected = self._repository.get_company_settlement_wallet(user.company_id)
        if selected is None:
            return SettlementWallet(
                wallet_type="EMBEDDED",
                address=embedded_wallet.address,
                embedded_wallet_address=embedded_wallet.address,
            )
        wallet_type, address = selected
        return SettlementWallet(
            wallet_type=wallet_type,
            address=address,
            embedded_wallet_address=embedded_wallet.address,
        )

    def update_settlement_wallet(
        self, email: str, payload: UpdateSettlementWalletRequest
    ) -> SettlementWallet:
        current = self.settlement_wallet_for_email(email)
        user = self._repository.get_onboarding_user_by_email(email)
        if user is None or user.company_id is None:
            raise OnboardingApiError(
                status.HTTP_401_UNAUTHORIZED,
                "MEMBER_SESSION_INVALID",
                "로그인 사용자 정보를 찾을 수 없습니다.",
            )
        if payload.wallet_type == "EMBEDDED":
            self._repository.clear_company_settlement_wallet(user.company_id)
            return SettlementWallet(
                wallet_type="EMBEDDED",
                address=current.embedded_wallet_address,
                embedded_wallet_address=current.embedded_wallet_address,
            )
        if not payload.address:
            raise OnboardingApiError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "EXTERNAL_WALLET_REQUIRED",
                "외부 Solana 지갑 주소를 연결해 주세요.",
            )
        try:
            address = str(Pubkey.from_string(payload.address))
        except ValueError as exc:
            raise OnboardingApiError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "WALLET_ADDRESS_INVALID",
                "유효한 Solana 지갑 주소를 입력해 주세요.",
            ) from exc
        self._repository.save_company_settlement_wallet(
            user.company_id, "EXTERNAL", address
        )
        return SettlementWallet(
            wallet_type="EXTERNAL",
            address=address,
            embedded_wallet_address=current.embedded_wallet_address,
        )

    async def withdraw_account_for_email(self, email: str) -> DeleteAccountResponse:
        user = self._repository.get_onboarding_user_by_email(email)
        if (
            user is None
            or user.company_id is None
            or user.onboarding_status is not OnboardingStatus.COMPLETED
        ):
            raise OnboardingApiError(
                status.HTTP_409_CONFLICT,
                "ACCOUNT_NOT_ACTIVE",
                "탈퇴할 활성 계정을 찾을 수 없습니다.",
            )
        await self._privy.delete_user(user.privy_user_id)
        self._repository.delete_onboarding_user(user.privy_user_id)
        return DeleteAccountResponse()

    async def onboard_company(
        self,
        principal: PrivyPrincipal,
        payload: OnboardCompanyRequest,
    ) -> OnboardingResponse:
        lock = await self._lock_for(principal.user_id)
        async with lock:
            user = await self._ensure_user(principal.user_id)
            if user.onboarding_status is OnboardingStatus.WITHDRAWN:
                await self._privy.delete_user(user.privy_user_id)
                self._repository.delete_onboarding_user(user.privy_user_id)
                raise OnboardingApiError(
                    status.HTTP_409_CONFLICT,
                    "ACCOUNT_DELETION_FINALIZED",
                    "기존 탈퇴 정보를 완전히 삭제했습니다. 이메일 인증부터 다시 진행해 주세요.",
                )
            if user.onboarding_status is OnboardingStatus.COMPLETED:
                raise OnboardingApiError(
                    status.HTTP_409_CONFLICT,
                    "ONBOARDING_ALREADY_COMPLETED",
                    "이미 가입이 완료된 Privy 사용자입니다.",
                )

            if payload.password is not None:
                self._repository.save_user_password_hash(
                    user.privy_user_id, hash_password(payload.password)
                )
            elif self._repository.get_user_password_hash(user.privy_user_id) is None:
                raise OnboardingApiError(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    "PASSWORD_REQUIRED",
                    "로그인에 사용할 비밀번호를 입력해 주세요.",
                )

            company = self._company_for(user) or Company(
                id=_id("cmp"),
                name=payload.company.name,
                type=payload.company.type,
                country_code=payload.company.country_code,
                registration_number=payload.company.registration_number,
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
            existing_wallet = self._repository.get_company_wallet(company.id)
            if (
                existing_wallet is not None
                and existing_wallet.privy_user_id == principal.user_id
            ):
                wallet = existing_wallet
            else:
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
