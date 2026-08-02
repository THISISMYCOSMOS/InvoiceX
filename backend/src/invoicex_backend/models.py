"""Public API DTOs and internal transfer records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator
from solders.pubkey import Pubkey


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    """Base DTO matching the frontend's lower-camel JSON contract."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class InvoiceStatus(StrEnum):
    DRAFT = "DRAFT"
    DOCUMENT_UPLOADING = "DOCUMENT_UPLOADING"
    DOCUMENT_ANALYZING = "DOCUMENT_ANALYZING"
    DOCUMENT_REVIEW_REQUIRED = "DOCUMENT_REVIEW_REQUIRED"
    BUYER_REVIEW = "BUYER_REVIEW"
    BUYER_VERIFIED = "BUYER_VERIFIED"
    RISK_ASSESSING = "RISK_ASSESSING"
    OFFER_READY = "OFFER_READY"
    RWA_ISSUED = "RWA_ISSUED"
    FUNDING = "FUNDING"
    FUNDED = "FUNDED"
    REPAYMENT_PENDING = "REPAYMENT_PENDING"
    SETTLING = "SETTLING"
    SETTLED = "SETTLED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    DISPUTED = "DISPUTED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class DocumentType(StrEnum):
    INVOICE = "INVOICE"
    CONTRACT = "CONTRACT"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    DELIVERY_PROOF = "DELIVERY_PROOF"


class UploadStatus(StrEnum):
    IDLE = "IDLE"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractedFieldStatus(StrEnum):
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class AnalysisStatus(StrEnum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskEligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    DISPUTED = "DISPUTED"


class OfferResponse(StrEnum):
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"


class LoginRole(StrEnum):
    SUPPLIER = "Supplier"
    BUYER = "Buyer"
    INVESTOR = "Investor"


class InvestmentCriteriaBuyer(ApiModel):
    id: str
    name: str


class LoginRequest(ApiModel):
    role: LoginRole
    email: str
    password: str


class LoginResponse(ApiModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: LoginRole
    email: str
    expires_at: str


class InvoiceParty(ApiModel):
    id: str
    name: str
    wallet_address: str | None = None
    vault_address: str | None = None


class InvoiceDocument(ApiModel):
    id: str
    invoice_id: str
    type: DocumentType
    file_name: str
    mime_type: str
    file_size: int = Field(ge=1)
    storage_url: str
    upload_status: UploadStatus


class Evidence(ApiModel):
    document_type: DocumentType
    page: int | None
    text: str | None


ExtractedValue = TypeVar("ExtractedValue")


class ExtractedField(ApiModel, Generic[ExtractedValue]):
    value: ExtractedValue | None
    evidence: Evidence | None = None
    status: ExtractedFieldStatus


class DocumentAnalysis(ApiModel):
    invoice_id: str
    status: AnalysisStatus
    invoice_number: ExtractedField[str]
    supplier_name: ExtractedField[str]
    buyer_name: ExtractedField[str]
    amount_krw: ExtractedField[int]
    due_date: ExtractedField[str]
    contract_number: ExtractedField[str]
    purchase_order_number: ExtractedField[str]
    delivery_completed: ExtractedField[bool]
    model_name: str | None = None
    prompt_version: str | None = None
    analyzed_at: str | None = None


class PositiveFactor(ApiModel):
    title: str
    description: str


class RiskFactor(ApiModel):
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    title: str
    description: str


class RiskPassport(ApiModel):
    invoice_id: str
    eligibility: RiskEligibility
    risk_score: int | None = Field(default=None, ge=0, le=100)
    score_direction: Literal["HIGHER_IS_SAFER"] = "HIGHER_IS_SAFER"
    positive_factors: list[PositiveFactor]
    risk_factors: list[RiskFactor]
    suggested_advance_rate_bps: int | None = Field(default=None, ge=0, le=10_000)
    suggested_advance_amount_usdc: int | None = Field(default=None, ge=0)
    model_name: str | None = None
    policy_version: str | None = None
    generated_at: str | None = None


class BlockchainTransaction(ApiModel):
    signature: str
    network: Literal["SOLANA_DEVNET"] = "SOLANA_DEVNET"
    status: TransactionStatus
    amount_usdc: int = Field(ge=0)
    from_address: str
    to_address: str
    explorer_url: str
    created_at: str
    sandbox: bool
    provider: Literal["PRIVY", "DIRECT", "MOCK"]


class Settlement(ApiModel):
    invoice_face_value_usdc: int
    investor_settlement_usdc: int
    platform_fee_usdc: int
    supplier_residual_usdc: int


class AgentTrace(ApiModel):
    id: str
    invoice_id: str
    source_agent: Literal[
        "DOCUMENT_AGENT",
        "RISK_AGENT",
        "TREASURY_AGENT",
        "SETTLEMENT_AGENT",
    ]
    target_agent: Literal["RISK_AGENT", "TREASURY_AGENT", "SETTLEMENT_AGENT"]
    status: Literal["SUBMITTED", "WORKING", "COMPLETED", "FAILED"]
    summary: str
    created_at: str
    completed_at: str | None = None


class RwaAsset(ApiModel):
    """The one-unit Devnet RWA issued for an eligible invoice."""

    invoice_id: str
    mint_address: str
    escrow_token_account: str
    status: Literal["ISSUED", "SOLD"]
    issue_transaction: BlockchainTransaction
    purchase_transaction: BlockchainTransaction | None = None
    owner_vault_address: str | None = None


class MandatePolicy(ApiModel):
    total_investment_limit_usdc: int = Field(gt=0)
    per_invoice_limit_usdc: int = Field(gt=0)
    buyer_allowlist: list[str] = Field(min_length=1)
    minimum_risk_score: int = Field(ge=0, le=100)
    maximum_remaining_term_days: int = Field(gt=0)
    expires_at: str


class InvestorMandate(ApiModel):
    id: str
    owner_wallet_address: str
    vault_address: str
    policy: MandatePolicy
    canonical_message: str
    signature: str
    status: Literal["ACTIVE", "REVOKED"] = "ACTIVE"
    created_at: str


class VaultBalance(ApiModel):
    owner_wallet_address: str
    vault_address: str
    available_usdc: int = Field(ge=0)
    updated_at: str


class AgentDecision(ApiModel):
    invoice_id: str
    mandate_id: str | None = None
    status: Literal["PENDING", "APPROVED", "REJECTED", "EXECUTED", "FAILED"]
    checks: dict[str, bool]
    amount_usdc: int = Field(default=0, ge=0)
    reason: str | None = None
    created_at: str


class Invoice(ApiModel):
    id: str
    supplier: InvoiceParty
    buyer: InvoiceParty
    investor: InvoiceParty
    invoice_amount_krw: int
    issue_date: str
    due_date: str
    delivery_date: str
    contract_number: str
    purchase_order_number: str
    status: InvoiceStatus
    verification_id: str | None
    documents: list[InvoiceDocument]
    analysis: DocumentAnalysis | None
    risk_passport: RiskPassport | None
    funding_transaction: BlockchainTransaction | None
    settlement_transaction: BlockchainTransaction | None
    settlement: Settlement | None
    agent_traces: list[AgentTrace]
    rwa_asset: RwaAsset | None = None
    agent_decision: AgentDecision | None = None


class Verification(ApiModel):
    id: str
    invoice_id: str
    status: VerificationStatus


class InvoiceResponse(ApiModel):
    invoice: Invoice


class InvoiceListResponse(ApiModel):
    items: list[Invoice]


class VerificationResponse(ApiModel):
    verification: Verification


class VerificationListResponse(ApiModel):
    items: list[Verification]


class OfferResponseRequest(ApiModel):
    response: OfferResponse
    supplier_wallet_address: str | None = None

    @field_validator("supplier_wallet_address")
    @classmethod
    def validate_supplier_wallet_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        address = value.strip()
        try:
            Pubkey.from_string(address)
        except ValueError as exc:
            raise ValueError("supplierWalletAddress must be a Solana address") from exc
        return address


class InvestorDepositPrepareRequest(ApiModel):
    investor_wallet_address: str
    amount_usdc: int = Field(gt=0)

    @field_validator("investor_wallet_address")
    @classmethod
    def validate_investor_wallet_address(cls, value: str) -> str:
        address = value.strip()
        try:
            Pubkey.from_string(address)
        except ValueError as exc:
            raise ValueError("investorWalletAddress must be a Solana address") from exc
        return address


class InvestorDepositPreparation(ApiModel):
    reference_id: str
    investor_wallet_address: str
    treasury_wallet_address: str
    usdc_mint: str
    amount_usdc: int
    decimals: int
    network: Literal["SOLANA_DEVNET"] = "SOLANA_DEVNET"


class InvestorDepositConfirmRequest(ApiModel):
    reference_id: str = Field(min_length=1, max_length=64)
    signature: str = Field(min_length=1, max_length=128)


class InvestorDeposit(ApiModel):
    reference_id: str
    investor_wallet_address: str
    treasury_wallet_address: str
    amount_usdc: int
    signature: str
    status: TransactionStatus
    network: Literal["SOLANA_DEVNET"] = "SOLANA_DEVNET"
    explorer_url: str
    confirmed_at: datetime


class SaveSupplierWalletRequest(ApiModel):
    wallet_address: str


class CreateMandateRequest(ApiModel):
    owner_wallet_address: str
    policy: MandatePolicy
    signature: str


class PrepareMandateRequest(ApiModel):
    owner_wallet_address: str
    policy: MandatePolicy


class MandateSigningPayload(ApiModel):
    canonical_message: str


class PrepareVaultDepositRequest(ApiModel):
    owner_wallet_address: str
    amount_usdc: int = Field(gt=0)


class VaultDepositPreparation(ApiModel):
    transaction_base64: str
    vault_address: str
    stablecoin_mint_address: str
    sponsored: bool = False
    sponsor_deposit_id: str | None = None
    sponsor_wallet_address: str | None = None


class ConfirmVaultDepositRequest(ApiModel):
    owner_wallet_address: str
    amount_usdc: int = Field(gt=0)
    signature: str


class SponsorVaultDepositRequest(ApiModel):
    owner_wallet_address: str
    sponsor_deposit_id: str
    signed_transaction_base64: str


class InvestorDashboard(ApiModel):
    investor_name: str
    automated_investment_active: bool
    mandate_status: Literal["DRAFT", "ACTIVE"]
    available_vault_usdc: int
    outstanding_principal_usdc: int
    due_within_30_days_usdc: int
    attention_required_count: int
    recent_agent_traces: list[AgentTrace]
    wallet_address: str | None = None
    vault_address: str | None = None
    latest_deposit: InvestorDeposit | None = None


class ErrorResponse(ApiModel):
    message: str
    details: list[dict[str, object]] | None = None


@dataclass(frozen=True, slots=True)
class UploadedDocument:
    """Validated upload passed from the API boundary into the domain service."""

    type: DocumentType
    file_name: str
    mime_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class ChainTransfer:
    """One USDC destination in a Solana transfer transaction."""

    to_address: str
    amount_usdc: int


@dataclass(frozen=True, slots=True)
class ChainTransferResult:
    """Provider-neutral Solana execution result."""

    signature: str
    status: TransactionStatus
    from_address: str
    provider: Literal["PRIVY", "MOCK"]
    sandbox: bool
