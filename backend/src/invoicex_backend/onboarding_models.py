"""Minimal company onboarding records and public API contracts."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import Field, field_validator

from invoicex_backend.models import ApiModel


class CompanyType(StrEnum):
    SUPPLIER = "SUPPLIER"
    BUYER = "BUYER"
    INVESTOR = "INVESTOR"


class OnboardingStatus(StrEnum):
    NEEDS_COMPANY_PROFILE = "NEEDS_COMPANY_PROFILE"
    PROVISIONING_EMBEDDED_WALLET = "PROVISIONING_EMBEDDED_WALLET"
    COMPLETED = "COMPLETED"


class Company(ApiModel):
    id: str
    name: str
    type: CompanyType
    business_registration_number: str
    kyb_status: str = "NOT_PERFORMED"
    status: str = "ACTIVE"


class OnboardingUser(ApiModel):
    id: str
    privy_user_id: str
    email: str
    name: str | None = None
    title: str | None = None
    phone: str | None = None
    company_id: str | None = None
    onboarding_status: OnboardingStatus
    wallet_idempotency_key: str | None = Field(default=None, exclude=True)


class CompanyWallet(ApiModel):
    id: str
    company_id: str
    privy_user_id: str
    wallet_type: str = "EMBEDDED"
    privy_wallet_id: str
    chain: str = "SOLANA"
    address: str
    status: str = "ACTIVE"


class LogicalVault(ApiModel):
    id: str
    investor_company_id: str
    available_usdc: int = Field(default=0, ge=0)
    status: str = "ACTIVE"


class CompanyInput(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    type: CompanyType
    business_registration_number: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("기업명을 입력해 주세요.")
        return normalized

    @field_validator("business_registration_number")
    @classmethod
    def normalize_business_number(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) != 10:
            raise ValueError("사업자등록번호는 숫자 10자리여야 합니다.")
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


class RepresentativeInput(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=100)
    phone: str

    @field_validator("name", "title")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("필수 정보를 입력해 주세요.")
        return normalized

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if re.fullmatch(r"\d{2,3}-\d{3,4}-\d{4}", normalized) is None:
            raise ValueError("연락처 형식이 올바르지 않습니다.")
        return normalized


class OnboardCompanyRequest(ApiModel):
    company: CompanyInput
    representative: RepresentativeInput


class AuthMeResponse(ApiModel):
    user: OnboardingUser
    company: Company | None
    embedded_wallet: CompanyWallet | None
    onboarding_status: OnboardingStatus
    next_path: str


class OnboardingResponse(AuthMeResponse):
    logical_vault: LogicalVault | None = None


def next_path(company: Company | None, status: OnboardingStatus) -> str:
    if company is None or status is not OnboardingStatus.COMPLETED:
        return "/signup"
    return {
        CompanyType.SUPPLIER: "/supplier",
        CompanyType.BUYER: "/buyer",
        CompanyType.INVESTOR: "/investor",
    }[company.type]
