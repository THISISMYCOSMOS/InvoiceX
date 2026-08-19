"""Minimal company onboarding records and public API contracts."""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from invoicex_backend.models import ApiModel


class CompanyType(StrEnum):
    SUPPLIER = "SUPPLIER"
    BUYER = "BUYER"
    INVESTOR = "INVESTOR"


class OnboardingStatus(StrEnum):
    NEEDS_COMPANY_PROFILE = "NEEDS_COMPANY_PROFILE"
    PROVISIONING_EMBEDDED_WALLET = "PROVISIONING_EMBEDDED_WALLET"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"


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


class SettlementWallet(ApiModel):
    wallet_type: Literal["EMBEDDED", "EXTERNAL"]
    address: str
    embedded_wallet_address: str


class UpdateSettlementWalletRequest(ApiModel):
    wallet_type: Literal["EMBEDDED", "EXTERNAL"]
    address: str | None = None


class DeleteAccountResponse(ApiModel):
    onboarding_status: Literal["WITHDRAWN"] = "WITHDRAWN"


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
        if normalized not in {"KR", "US"}:
            raise ValueError("현재 지원하는 국가 코드는 KR 또는 US입니다.")
        return normalized

    @field_validator("registration_number")
    @classmethod
    def normalize_registration_number(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).upper()
        normalized = re.sub(r"[^A-Z0-9]", "", normalized)
        if not 2 <= len(normalized) <= 50:
            raise ValueError("기업 등록번호를 2~50자의 영문 또는 숫자로 입력해 주세요.")
        return normalized

    @model_validator(mode="after")
    def validate_registration_number_for_country_and_role(self) -> CompanyInput:
        required_country_code = "KR" if self.type == CompanyType.SUPPLIER else "US"
        if self.country_code != required_country_code:
            if self.type == CompanyType.SUPPLIER:
                raise ValueError("공급기업은 국내 사업자등록번호(KR)로 등록해 주세요.")
            raise ValueError("구매기업 및 투자기관은 미국 EIN(US)으로 등록해 주세요.")
        if self.country_code == "KR" and re.fullmatch(r"\d{10}", self.registration_number) is None:
            raise ValueError("국내 사업자등록번호는 숫자 10자리(000-00-00000)로 입력해 주세요.")
        if self.country_code == "US" and re.fullmatch(r"\d{9}", self.registration_number) is None:
            raise ValueError("미국 EIN은 숫자 9자리(00-0000000)로 입력해 주세요.")
        return self


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
    password: str | None = Field(default=None, min_length=8, max_length=128)
    embedded_wallet_address: str | None = None


class LinkEmbeddedWalletRequest(ApiModel):
    address: str


class UpdateCompanyProfileRequest(ApiModel):
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
