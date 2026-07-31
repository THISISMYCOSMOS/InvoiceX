"""Public API DTOs and internal transfer records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


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


class BuyerChecklistChoice(StrEnum):
    """One row of the Buyer verification checklist.

    MATCH also covers the affirmative option on the two rows the UI labels
    differently: 납품 완료 "확인" and 분쟁 "없음".
    """

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"


class BuyerChecklist(ApiModel):
    """The six rows BuyerInvoiceDetailPage collects before Confirm.

    Every row defaults to MATCH so an older client that sends no body keeps the
    previous "everything agrees" behaviour.
    """

    transaction: BuyerChecklistChoice = BuyerChecklistChoice.MATCH
    supplier: BuyerChecklistChoice = BuyerChecklistChoice.MATCH
    amount: BuyerChecklistChoice = BuyerChecklistChoice.MATCH
    due_date: BuyerChecklistChoice = BuyerChecklistChoice.MATCH
    delivery: BuyerChecklistChoice = BuyerChecklistChoice.MATCH
    dispute: BuyerChecklistChoice = BuyerChecklistChoice.MATCH

    def with_transaction_confirmed(self) -> BuyerChecklist:
        """Pin the transaction row positive.

        The demo invoice is synthetic data we insert ourselves, so "the
        transaction does not exist" is not a reachable outcome and must never
        turn the happy path into a rejection.
        """

        return self.model_copy(update={"transaction": BuyerChecklistChoice.MATCH})

    @property
    def dispute_reported(self) -> bool:
        return self.dispute is BuyerChecklistChoice.MISMATCH

    def mismatched_rows(self) -> list[str]:
        """Rows the buyer marked as disagreeing, excluding the dispute row."""

        rows = {
            "supplier": "공급기업 정보",
            "amount": "인보이스 금액",
            "due_date": "만기일",
            "delivery": "납품 완료",
        }
        return [
            label
            for field, label in rows.items()
            if getattr(self, field) is BuyerChecklistChoice.MISMATCH
        ]


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
    provider: Literal["PRIVY", "MOCK"]


class Settlement(ApiModel):
    invoice_face_value_usdc: int
    investor_settlement_usdc: int
    platform_fee_usdc: int
    supplier_residual_usdc: int


class PaymentInstructions(ApiModel):
    """Mock KRW deposit details shown on the Buyer maturity payment screen.

    The defaults double as the fallback for snapshots written before this field
    existed, so an upgrade does not invalidate a running demo's state file.
    """

    bank_name: str = "OOBank"
    virtual_account: str = "123-456-789012"
    account_holder: str = "InvoiceX Settlement Partner"


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
    verification_requested_at: str | None = None
    payment_instructions: PaymentInstructions = Field(
        default_factory=PaymentInstructions
    )
    documents: list[InvoiceDocument]
    analysis: DocumentAnalysis | None
    risk_passport: RiskPassport | None
    funding_transaction: BlockchainTransaction | None
    settlement_transaction: BlockchainTransaction | None
    settlement: Settlement | None
    agent_traces: list[AgentTrace]


class Verification(ApiModel):
    id: str
    invoice_id: str
    status: VerificationStatus
    checklist: BuyerChecklist | None = None


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


class ConfirmVerificationRequest(ApiModel):
    """Optional body for Buyer confirm; omitting it means every row agreed."""

    checklist: BuyerChecklist = Field(default_factory=BuyerChecklist)


class InvestorMandate(ApiModel):
    """The AP2 investment policy InvestorSetupPage collects.

    Field names mirror the form inputs. `maximumTermDays` is a number here even
    though the form currently renders free text ("120 days"), because the policy
    has to compare it against a due date.
    """

    deposit_usdc: int = Field(ge=0)
    total_limit_usdc: int = Field(ge=0)
    per_invoice_limit_usdc: int = Field(gt=0)
    buyer_allowlist: list[str]
    minimum_risk_score: int = Field(ge=0, le=100)
    maximum_term_days: int = Field(gt=0)
    policy_expires_on: str
    mandate_id: str = "DEMO-MANDATE-001"
    policy_hash: str = "demo-policy-v1"
    status: Literal["DRAFT", "SIGNED", "ACTIVE"] = "ACTIVE"


class InvestorMandateResponse(ApiModel):
    mandate: InvestorMandate


class InvestorDashboard(ApiModel):
    investor_name: str
    automated_investment_active: bool
    mandate_status: Literal["DRAFT", "SIGNED", "ACTIVE"]
    # The address settlement actually pays out to, so the UI never shows a
    # different wallet than the one USDC moves through.
    vault_address: str
    available_vault_usdc: int
    outstanding_principal_usdc: int
    due_within_30_days_usdc: int
    recent_agent_traces: list[AgentTrace]


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
