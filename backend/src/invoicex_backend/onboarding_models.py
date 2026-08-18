"""Minimal company onboarding records and public API contracts."""

from __future__ import annotations

import re
import unicodedata
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
    country_code: str
    registration_number: str
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
    country_code: str
    registration_number: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("기업명을 입력해 주세요.")
        return normalized

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if re.fullmatch(r"[A-Z]{2}", normalized) is None:
            raise ValueError("국가 코드는 영문 2자리로 입력해 주세요.")
        return normalized

    @field_validator("registration_number")
    @classmethod
    def normalize_registration_number(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).upper()
        normalized = re.sub(r"[^A-Z0-9]", "", normalized)
        if not 2 <= len(normalized) <= 50:
            raise ValueError("기업 등록번호를 2~50자의 영문 또는 숫자로 입력해 주세요.")
        return normalized


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
        if re.fullmatch(r"\+?[0-9][0-9 ()-]{6,24}", normalized) is None:
            raise ValueError("국가번호를 포함한 국제 전화번호 또는 국내 전화번호를 입력해 주세요.")
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
