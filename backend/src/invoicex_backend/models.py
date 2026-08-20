"""Public API DTOs and internal transfer records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
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
    REJECTED = "REJECTED"
    REVIEW_REQUESTED = "REVIEW_REQUESTED"
    RWA_ISSUED = "RWA_ISSUED"
    FUNDING = "FUNDING"
    FUNDED = "FUNDED"
    REPAYMENT_PENDING = "REPAYMENT_PENDING"
    SETTLING = "SETTLING"
    SETTLED = "SETTLED"
    SETTLEMENT_FAILED = "SETTLEMENT_FAILED"
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
    REJECTED = "REJECTED"
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
    auth_mode: Literal["DEMO", "MEMBER"]
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
    amount: ExtractedField[int]
    currency: ExtractedField[str]
    due_date: ExtractedField[str]
    contract_number: ExtractedField[str]
    purchase_order_number: ExtractedField[str]
    delivery_completed: ExtractedField[bool]
    model_name: str | None = None
    prompt_version: str | None = None
    analyzed_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def read_legacy_krw_amount(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        legacy_amount = normalized.pop("amountKrw", normalized.pop("amount_krw", None))
        if "amount" not in normalized and legacy_amount is not None:
            normalized["amount"] = legacy_amount
        if "currency" not in normalized:
            status = (
                legacy_amount.get("status", ExtractedFieldStatus.MATCHED)
                if isinstance(legacy_amount, dict)
                else ExtractedFieldStatus.MATCHED
            )
            normalized["currency"] = {"value": "KRW", "status": status}
        return normalized


class PositiveFactor(ApiModel):
    title: str
    description: str


class RiskFactor(ApiModel):
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    title: str
    description: str


class RiskScoreFactor(ApiModel):
    key: str
    label: str
    score: int | None = Field(default=None, ge=0)
    max_score: int = Field(gt=0)
    source: Literal[
        "SYNTHETIC_DEMO_DATA",
        "INVOICE_DATA",
        "INVOICEX_DATA",
        "DOCUMENT_AGENT",
    ]
    detail: str | None = None
    synthetic: bool = False


class HardGateCheck(ApiModel):
    key: str
    label: str
    passed: bool
    reason: str | None = None


class HardGateResult(ApiModel):
    passed: bool
    checks: list[HardGateCheck] = Field(default_factory=list)
    failure_reasons: list[str] = Field(default_factory=list)


class EarlySettlementTerms(ApiModel):
    face_value_usdc: int = Field(ge=0)
    discount_amount_usdc: int = Field(ge=0)
    discount_rate_bps: int = Field(ge=0, le=10_000)
    investor_required_return_usdc: int = Field(ge=0)
    platform_fee_usdc: int = Field(ge=0)
    reserve_amount_usdc: int = Field(ge=0)
    reserve_rate_bps: int = Field(ge=0, le=10_000)
    initial_advance_usdc: int = Field(ge=0)
    expected_reserve_return_usdc: int = Field(ge=0)
    expected_final_proceeds_usdc: int = Field(ge=0)
    remaining_term_days: int | None = Field(default=None, ge=0)
    sofr_rate_bps: int | None = Field(default=None, ge=0)
    risk_spread_bps: int | None = Field(default=None, ge=0)
    country_legal_spread_bps: int | None = Field(default=None, ge=0)
    annual_expected_yield_bps: int | None = Field(default=None, ge=0)
    expected_investor_return_usdc: int | None = Field(default=None, ge=0)
    purchase_amount_usdc: int | None = Field(default=None, ge=0)
    supplier_expected_settlement_usdc: int | None = Field(default=None, ge=0)
    settlement_asset: Literal["USDC"] = "USDC"
    network: Literal["SOLANA_DEVNET"] = "SOLANA_DEVNET"


class RiskPassport(ApiModel):
    invoice_id: str
    eligibility: RiskEligibility
    risk_score: int | None = Field(default=None, ge=0, le=100)
    score_direction: Literal["HIGHER_IS_SAFER"] = "HIGHER_IS_SAFER"
    positive_factors: list[PositiveFactor]
    risk_factors: list[RiskFactor]
    suggested_advance_rate_bps: int | None = Field(default=None, ge=0, le=10_000)
    suggested_advance_amount_usdc: int | None = Field(default=None, ge=0)
    invoice_face_value_usdc: int | None = Field(default=None, ge=0)
    source_currency_to_usdc_rate: float | None = Field(default=None, gt=0)
    data_coverage_bps: int = Field(default=0, ge=0, le=10_000)
    score_factors: list[RiskScoreFactor] = Field(default_factory=list)
    hard_gate: HardGateResult | None = None
    early_settlement_terms: EarlySettlementTerms | None = None
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


class BuyerPaymentTransfer(ApiModel):
    recipient_wallet_address: str
    amount_usdc: int = Field(gt=0)
    amount_base_units: int = Field(gt=0)


class BuyerPaymentPreparation(ApiModel):
    invoice_id: str
    buyer_wallet_address: str
    settlement_wallet_address: str
    usdc_mint_address: str
    amount_usdc: int = Field(gt=0)
    amount_base_units: int = Field(gt=0)
    decimals: int = Field(ge=0, le=18)
    due_date: str
    transfers: list[BuyerPaymentTransfer] = Field(min_length=1)
    demo_due_date_bypass: bool = False


class BuyerPaymentConfirmRequest(ApiModel):
    signature: str = Field(min_length=20, max_length=200)


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
    status: Literal["ISSUED", "SOLD", "SETTLED"]
    issue_transaction: BlockchainTransaction
    face_value_usdc: int | None = Field(default=None, ge=0)
    issuance_price_usdc: int | None = Field(default=None, ge=0)
    purchase_transaction: BlockchainTransaction | None = None
    owner_vault_address: str | None = None
    owner_wallet_address: str | None = None


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

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_execution_metadata(cls, value: object) -> object:
        """Keep policy checks boolean-only while reading decisions saved by v1.

        The initial Devnet purchase path wrote transfer bookkeeping values into
        ``checks``.  Those values were never policy checks and made persisted
        decisions unreadable because this field correctly accepts booleans
        only.  Strip the old values at the persistence boundary so a deploy can
        recover existing invoices without mutating their historical records.
        """

        if not isinstance(value, dict):
            return value
        raw_checks = value.get("checks")
        if not isinstance(raw_checks, dict):
            return value
        normalized = dict(value)
        checks = dict(raw_checks)
        for key in ("demoTransferCapApplied", "quotedAmountUsdc", "onchainAmountUsdc"):
            checks.pop(key, None)
        normalized["checks"] = checks
        return normalized


class Invoice(ApiModel):
    id: str
    supplier: InvoiceParty
    buyer: InvoiceParty
    investor: InvoiceParty
    invoice_amount: int
    currency: str
    issue_date: str
    due_date: str
    delivery_date: str
    contract_number: str
    purchase_order_number: str
    status: InvoiceStatus
    verification_id: str | None
    verification_requested_at: str | None = None
    verification_confirmed_at: str | None = None
    verification_rejected_at: str | None = None
    rejection_reason_code: str | None = None
    rejection_reason_detail: str | None = None
    review_requested_at: str | None = None
    documents: list[InvoiceDocument]
    analysis: DocumentAnalysis | None
    risk_passport: RiskPassport | None
    funding_transaction: BlockchainTransaction | None
    settlement_transaction: BlockchainTransaction | None
    buyer_payment_transaction: BlockchainTransaction | None = None
    investor_payout_transaction: BlockchainTransaction | None = None
    platform_fee_transaction: BlockchainTransaction | None = None
    buyer_paid_at: str | None = None
    settlement: Settlement | None
    agent_traces: list[AgentTrace]
    rwa_asset: RwaAsset | None = None
    agent_decision: AgentDecision | None = None

    @model_validator(mode="before")
    @classmethod
    def read_legacy_krw_amount(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        legacy_amount = normalized.pop(
            "invoiceAmountKrw", normalized.pop("invoice_amount_krw", None)
        )
        if "invoiceAmount" not in normalized and "invoice_amount" not in normalized:
            normalized["invoice_amount"] = legacy_amount
        normalized.setdefault("currency", "KRW")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not 3 <= len(normalized) <= 10 or not normalized.isalpha():
            raise ValueError("통화 코드는 영문 3~10자리여야 합니다.")
        return normalized


class Verification(ApiModel):
    id: str
    invoice_id: str
    status: VerificationStatus
    created_at: str | None = None
    rejection_reason_code: str | None = None
    rejection_reason_detail: str | None = None
    responded_at: str | None = None


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


class RejectVerificationRequest(ApiModel):
    reason_code: Literal[
        "DUPLICATE_INVOICE",
        "DOCUMENT_MISMATCH",
        "DELIVERY_INCOMPLETE",
        "AMOUNT_ERROR",
        "DUE_DATE_ERROR",
        "SUSPECTED_ASSIGNMENT",
        "OTHER",
    ]
    detail: str | None = Field(default=None, max_length=1000)


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
    provider: Literal["PRIVY", "DIRECT", "MOCK"]
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
    code: str | None = None
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
