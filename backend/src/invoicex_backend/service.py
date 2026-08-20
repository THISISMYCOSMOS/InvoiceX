"""Invoice aggregate service and state-transition orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import secrets
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

BUSINESS_TIMEZONE = timezone(timedelta(hours=9))

from invoicex_agents.exceptions import AgentError
from invoicex_agents.models.common import SourceEvidence
from invoicex_agents.models.document import DocumentAnalysisResult
from invoicex_agents.models.risk import RiskAnalysisRequest, RiskFactorContext
from solders.pubkey import Pubkey
from solders.signature import Signature

from invoicex_backend.agent_activity import (
    AgentActivityItem,
    AgentActivityTimeline,
    AgentHandoff,
    AgentRun,
    AgentRunStatus,
    AgentToolCall,
    AgentTrigger,
    ToolCallStatus,
)
from invoicex_backend.agents import AgentDocument, AgentGateway
from invoicex_backend.auth import AuthenticatedIdentity
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import (
    DocumentValidationError,
    IntegrationError,
    NotFoundError,
    StateConflictError,
)
from invoicex_backend.hard_gate import HardGateInput, evaluate_hard_gate
from invoicex_backend.models import (
    AgentDecision,
    AgentTrace,
    AnalysisStatus,
    BlockchainTransaction,
    BuyerPaymentPreparation,
    BuyerPaymentTransfer,
    ChainTransfer,
    ChainTransferResult,
    ConfirmVaultDepositRequest,
    CreateMandateRequest,
    DocumentAnalysis,
    DocumentType,
    EarlySettlementTerms,
    ExtractedFieldStatus,
    InvestorDashboard,
    InvestorMandate,
    Invoice,
    InvoiceParty,
    InvoiceStatus,
    LoginRole,
    MandatePolicy,
    OfferResponse,
    PositiveFactor,
    RiskFactor,
    RiskPassport,
    RiskScoreFactor,
    RwaAsset,
    Settlement,
    SponsorVaultDepositRequest,
    TransactionStatus,
    UploadedDocument,
    VaultBalance,
    Verification,
    VerificationStatus,
)
from invoicex_backend.money import (
    base_units_string,
    base_units_to_usdc,
    parse_usdc,
    usdc_to_base_units,
)
from invoicex_backend.policy import RiskDecision
from invoicex_backend.pricing import (
    PricingPolicy,
    calculate_dynamic_pricing,
)
from invoicex_backend.repository import RwaRepository, SQLiteRwaRepository
from invoicex_backend.risk_scoring import (
    DeterministicRiskScoringProvider,
    RiskScoringProvider,
    RiskScoringRequest,
)
from invoicex_backend.solana import SolanaGateway
from invoicex_backend.storage import DocumentStorage
from invoicex_backend.valuation import value_invoice_in_usdc

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = frozenset({"application/pdf", "image/jpeg", "image/jpg", "image/png"})
REQUIRED_DOCUMENT_TYPES = frozenset(DocumentType)
TraceSource = Literal[
    "DOCUMENT_AGENT",
    "RISK_AGENT",
    "TREASURY_AGENT",
    "SETTLEMENT_AGENT",
]
TraceTarget = Literal["RISK_AGENT", "TREASURY_AGENT", "SETTLEMENT_AGENT"]
TraceStatus = Literal["SUBMITTED", "WORKING", "COMPLETED", "FAILED"]


@dataclass(frozen=True, slots=True)
class PendingSponsoredDeposit:
    owner_wallet_address: str
    amount_base_units: int
    prepared_transaction_base64: str
    expires_at: datetime


class InvoiceService:
    """Own Invoice state and coordinate Agent and chain adapters."""

    def __init__(
        self,
        *,
        settings: BackendSettings,
        agent_gateway: AgentGateway,
        solana_gateway: SolanaGateway,
        storage: DocumentStorage,
        repository: RwaRepository | None = None,
        risk_scoring_provider: RiskScoringProvider | None = None,
    ) -> None:
        self._settings = settings
        self._agents = agent_gateway
        self._solana = solana_gateway
        self._storage = storage
        self._repository = repository or SQLiteRwaRepository(settings.rwa_database_path)
        self._risk_scoring = risk_scoring_provider or DeterministicRiskScoringProvider()
        self._pricing_policy = PricingPolicy(
            sofr_bps=settings.mvp_sofr_bps,
            sofr_as_of=settings.sofr_as_of,
            sofr_source=settings.sofr_source,
            risk_spreads_bps=(
                (90, settings.risk_spread_90_bps),
                (80, settings.risk_spread_80_bps),
                (70, settings.risk_spread_70_bps),
            ),
            country_legal_spread_bps=settings.pilot_country_legal_spread_bps,
            platform_fee_share_bps=settings.platform_fee_share_bps,
        )
        self._invoices: dict[str, Invoice] = {}
        self._agent_analyses: dict[str, DocumentAnalysisResult] = {}
        self._verifications: dict[str, Verification] = {}
        self._invoice_locks: dict[str, asyncio.Lock] = {}
        self._sequence_lock = asyncio.Lock()
        self._invoice_sequence = 0
        self._verification_sequence = 0
        self._document_sequence = 0
        self._trace_sequence = 0
        self._sponsored_deposit_intents: dict[str, PendingSponsoredDeposit] = {}
        self._sponsored_deposit_lock = asyncio.Lock()
        self._restore_persisted_state()

    def _restore_persisted_state(self) -> None:
        """Rehydrate invoices, analyses, and verifications from the repository
        so a process restart does not orphan RWA/decision rows or reset the
        id sequences (which would collide with previously issued ids)."""

        for invoice in self._repository.list_invoices():
            self._invoices[invoice.id] = invoice
        for verification in self._repository.list_verifications():
            self._verifications[verification.id] = verification
        self._agent_analyses = self._repository.list_analyses()
        self._reconcile_registered_buyer_companies()

        self._invoice_sequence = self._max_id_suffix(self._invoices.keys(), "INV-")
        self._verification_sequence = self._max_id_suffix(self._verifications.keys(), "VER-")
        document_ids = [
            document.id for invoice in self._invoices.values() for document in invoice.documents
        ]
        self._document_sequence = self._max_id_suffix(document_ids, "DOC-")
        trace_ids = [
            trace.id for invoice in self._invoices.values() for trace in invoice.agent_traces
        ]
        self._trace_sequence = self._max_id_suffix(trace_ids, "TRACE-")

    def _reconcile_registered_buyer_companies(self) -> None:
        for invoice in self._invoices.values():
            company = self._repository.find_company_by_name(invoice.buyer.name, "BUYER")
            if company is None or invoice.buyer.id == company.id:
                continue
            invoice.buyer = invoice.buyer.model_copy(update={"id": company.id})
            self._save_invoice(invoice)

    @staticmethod
    def _max_id_suffix(ids: Iterable[str], prefix: str) -> int:
        """Return the largest trailing integer among ids starting with prefix.

        Ids that don't match the expected shape are skipped rather than
        raising, since a corrupt or unexpected row should not block startup.
        """

        max_value = 0
        for value in ids:
            if not value.startswith(prefix):
                continue
            match = re.search(r"(\d+)$", value)
            if match is None:
                continue
            try:
                number = int(match.group(1))
            except ValueError:
                continue
            max_value = max(max_value, number)
        return max_value

    def _save_invoice(self, invoice: Invoice) -> None:
        self._repository.save_invoice(invoice)

    async def create_invoice(
        self,
        uploads: list[UploadedDocument],
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        self._validate_uploads(uploads)
        invoice_id, document_ids = await self._reserve_invoice_ids(len(uploads))
        now = datetime.now(UTC)
        supplier = InvoiceParty(
            id="SUPPLIER_ALPHA",
            name="Alpha Components",
            wallet_address=self._settings.supplier_wallet_address,
        )
        if identity is not None and identity.source == "PRIVY":
            if identity.company_id is None or identity.company_name is None:
                raise StateConflictError("가입한 공급기업 정보를 확인할 수 없습니다.")
            supplier = InvoiceParty(
                id=identity.company_id,
                name=identity.company_name,
                wallet_address=identity.wallet_address,
            )
        invoice = Invoice(
            id=invoice_id,
            supplier=supplier,
            buyer=InvoiceParty(id="BUYER_PRIME", name="확인 필요"),
            investor=InvoiceParty(
                id="INVESTOR_NOVA",
                name="Nova Capital",
                vault_address=self._settings.investor_settlement_wallet_address,
            ),
            invoice_amount=0,
            # This provisional value is never used as extracted data. It only
            # satisfies the Invoice schema until Document Agent returns.
            currency="UNKNOWN",
            issue_date=now.date().isoformat(),
            due_date=(now + timedelta(days=90)).date().isoformat(),
            delivery_date=(now - timedelta(days=5)).date().isoformat(),
            contract_number="",
            purchase_order_number="",
            status=InvoiceStatus.DOCUMENT_ANALYZING,
            verification_id=None,
            verification_requested_at=None,
            verification_confirmed_at=None,
            documents=[],
            analysis=None,
            risk_passport=None,
            funding_transaction=None,
            settlement_transaction=None,
            settlement=None,
            agent_traces=[],
        )
        self._invoices[invoice_id] = invoice

        try:
            stored_documents = await asyncio.gather(
                *[
                    self._storage.store(
                        document_id=document_id,
                        invoice_id=invoice_id,
                        upload=upload,
                    )
                    for document_id, upload in zip(document_ids, uploads, strict=True)
                ]
            )
            invoice.documents = list(stored_documents)
            self._save_invoice(invoice)
        except OSError as exc:
            invoice.status = InvoiceStatus.ERROR
            self._save_invoice(invoice)
            raise IntegrationError("업로드 문서를 저장하지 못했습니다.") from exc
        return self._copy_invoice(invoice)

    async def analyze_invoice_documents(self, invoice_id: str) -> Invoice:
        """Analyze a persisted document set once; safe for Cloud Tasks retries."""

        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            if invoice.status is not InvoiceStatus.DOCUMENT_ANALYZING:
                return self._copy_invoice(invoice)
            try:
                document_bytes = await asyncio.gather(
                    *[self._storage.load(document) for document in invoice.documents]
                )
                agent_documents = [
                    AgentDocument(
                        document_id=document.id,
                        type=document.type,
                        mime_type=document.mime_type,
                        data=data,
                    )
                    for document, data in zip(invoice.documents, document_bytes, strict=True)
                ]
                agent_result = await self._agents.analyze_documents(invoice_id, agent_documents)
            except AgentError as exc:
                invoice.status = InvoiceStatus.ERROR
                self._save_invoice(invoice)
                raise IntegrationError(f"Gemini 문서 분석에 실패했습니다: {exc}") from exc
            except OSError as exc:
                invoice.status = InvoiceStatus.ERROR
                self._save_invoice(invoice)
                raise IntegrationError("저장된 업로드 문서를 불러오지 못했습니다.") from exc

            self._agent_analyses[invoice_id] = agent_result
            self._repository.save_analysis(invoice_id, agent_result)
            invoice.analysis = self._to_frontend_analysis(
                invoice_id,
                agent_result,
                {document.document_id: document.type for document in agent_documents},
            )
            authenticated_supplier_name = (
                invoice.supplier.name if invoice.supplier.id != "SUPPLIER_ALPHA" else None
            )
            self._apply_extracted_metadata(invoice, agent_result)
            if authenticated_supplier_name is not None:
                invoice.supplier.name = authenticated_supplier_name
            if self._matching_prior_invoice_numbers(invoice):
                invoice.status = InvoiceStatus.BLOCKED
                invoice.rejection_reason_code = "DUPLICATE_INVOICE"
                invoice.rejection_reason_detail = (
                    "동일한 인보이스 번호가 이미 등록되어 있습니다."
                )
            else:
                invoice.status = InvoiceStatus.DOCUMENT_REVIEW_REQUIRED
            self._append_trace(
                invoice,
                source="DOCUMENT_AGENT",
                target="RISK_AGENT",
                status="COMPLETED",
                summary="Gemini 문서 분석과 근거 연결을 완료했습니다.",
            )
            self._record_completed_agent_run(
                invoice_id=invoice.id,
                trigger=AgentTrigger.INVOICE_CREATED,
                tool_name="analyze_documents",
                summary="문서 분석과 교차 검증을 완료했습니다.",
                source_agent="DOCUMENT_AGENT",
                target_agent="RISK_AGENT",
            )
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    async def replace_invoice_documents(
        self,
        invoice_id: str,
        uploads: list[UploadedDocument],
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        """Replace an unsubmitted invoice's documents and discard its analysis."""

        self._validate_uploads(uploads)
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            self.assert_invoice_access(invoice, identity)
            if invoice.status is not InvoiceStatus.DOCUMENT_REVIEW_REQUIRED:
                raise StateConflictError("문서는 추출 정보 확인 단계에서만 수정할 수 있습니다.")
            async with self._sequence_lock:
                document_ids = []
                for _ in uploads:
                    self._document_sequence += 1
                    document_ids.append(f"DOC-{str(self._document_sequence).zfill(3)}")
            try:
                stored_documents = await asyncio.gather(
                    *[
                        self._storage.store(document_id=document_id, invoice_id=invoice_id, upload=upload)
                        for document_id, upload in zip(document_ids, uploads, strict=True)
                    ]
                )
            except OSError as exc:
                raise IntegrationError("교체할 업로드 문서를 저장하지 못했습니다.") from exc

            invoice.documents = list(stored_documents)
            invoice.analysis = None
            invoice.invoice_amount = 0
            invoice.currency = "UNKNOWN"
            invoice.contract_number = ""
            invoice.purchase_order_number = ""
            invoice.status = InvoiceStatus.DOCUMENT_ANALYZING
            self._agent_analyses.pop(invoice_id, None)
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    async def run_agent_task(self, invoice_id: str, trigger: AgentTrigger) -> None:
        if trigger is not AgentTrigger.INVOICE_CREATED:
            raise StateConflictError("지원하지 않는 비동기 Agent 작업입니다.")
        await self.analyze_invoice_documents(invoice_id)

    def list_invoices(
        self,
        identity: AuthenticatedIdentity | None = None,
    ) -> list[Invoice]:
        self._reconcile_buyer_invoices(identity)
        invoices: list[Invoice] = []
        for invoice in sorted(
            self._invoices.values(),
            key=lambda item: item.id,
            reverse=True,
        ):
            if not self._can_access_invoice(invoice, identity):
                continue
            self._ensure_dynamic_pricing(invoice)
            invoices.append(self._copy_invoice(invoice))
        return invoices

    def get_invoice(
        self,
        invoice_id: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        self._reconcile_buyer_invoices(identity)
        invoice = self._invoice(invoice_id)
        self.assert_invoice_access(invoice, identity)
        self._ensure_dynamic_pricing(invoice)
        return self._copy_invoice(invoice)

    def save_supplier_wallet(
        self,
        wallet_address: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> None:
        self._validate_wallet_address(wallet_address)
        self.assert_wallet_ownership(wallet_address, identity)
        if identity is not None and identity.source == "PRIVY":
            return
        self._repository.save_supplier_wallet(wallet_address)

    def create_mandate(self, request: CreateMandateRequest) -> InvestorMandate:
        self._validate_wallet_address(request.owner_wallet_address)
        expires_at = self._parse_iso_date(request.policy.expires_at, "Mandate 만료일")
        if expires_at < datetime.now(UTC).date():
            raise StateConflictError("만료된 날짜로 Mandate를 활성화할 수 없습니다.")
        message = self._canonical_mandate_message(request.owner_wallet_address, request.policy)
        try:
            is_valid = Signature.from_string(request.signature).verify(
                Pubkey.from_string(request.owner_wallet_address), message.encode("utf-8")
            )
        except ValueError as exc:
            raise StateConflictError(
                "Mandate 서명 또는 지갑 주소 형식이 올바르지 않습니다."
            ) from exc
        if not is_valid:
            raise StateConflictError("Mandate 서명을 검증하지 못했습니다.")
        now = datetime.now(UTC).isoformat()
        mandate = InvestorMandate(
            id=f"MAN-{hashlib.sha256(message.encode('utf-8')).hexdigest()[:16]}",
            owner_wallet_address=request.owner_wallet_address,
            vault_address=self._solana.vault_address,
            policy=request.policy,
            canonical_message=message,
            signature=request.signature,
            created_at=now,
        )
        self._repository.save_mandate(mandate)
        self.provision_investor_vault(mandate.owner_wallet_address)
        return mandate

    def prepare_mandate_message(
        self,
        *,
        owner_wallet_address: str,
        policy: MandatePolicy,
    ) -> str:
        self._validate_wallet_address(owner_wallet_address)
        expires_at = self._parse_iso_date(policy.expires_at, "Mandate 만료일")
        if expires_at < datetime.now(UTC).date():
            raise StateConflictError("만료된 날짜로 Mandate를 준비할 수 없습니다.")
        return self._canonical_mandate_message(owner_wallet_address, policy)

    def active_mandate_for_wallet(self, owner_wallet_address: str) -> InvestorMandate | None:
        self._validate_wallet_address(owner_wallet_address)
        for mandate in self._repository.active_mandates():
            if mandate.owner_wallet_address == owner_wallet_address:
                return mandate
        return None

    def get_vault(self, owner_wallet_address: str) -> VaultBalance:
        return self.provision_investor_vault(owner_wallet_address)

    def provision_investor_vault(self, owner_wallet_address: str) -> VaultBalance:
        """Create the investor's balance ledger as soon as their wallet is known."""
        self._validate_wallet_address(owner_wallet_address)
        existing = self._repository.get_vault(owner_wallet_address)
        if existing is not None:
            if existing.vault_address.startswith("DEMO_") and self._solana.mode != "mock":
                migrated = existing.model_copy(
                    update={
                        "vault_address": self._solana.vault_address,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                self._repository.save_vault(migrated)
                return migrated
            return existing
        vault = VaultBalance(
            owner_wallet_address=owner_wallet_address,
            vault_address=self._solana.vault_address,
            available_usdc=0,
            available_base_units="0",
            updated_at=datetime.now(UTC).isoformat(),
        )
        self._repository.save_vault(vault)
        return vault

    @property
    def vault_provider(self) -> Literal["PRIVY", "DIRECT", "MOCK"]:
        return {"privy": "PRIVY", "direct": "DIRECT", "mock": "MOCK"}[self._solana.mode]  # type: ignore[return-value]

    async def prepare_vault_deposit(self, *, owner_wallet_address: str, amount_usdc: Decimal):
        self._validate_wallet_address(owner_wallet_address)
        amount_base_units = usdc_to_base_units(amount_usdc)
        prepared = await self._solana.prepare_vault_deposit(
            owner_wallet_address=owner_wallet_address,
            amount_base_units=amount_base_units,
        )
        if not prepared.sponsored:
            return prepared
        sponsor_deposit_id = secrets.token_urlsafe(24)
        async with self._sponsored_deposit_lock:
            self._sponsored_deposit_intents[sponsor_deposit_id] = PendingSponsoredDeposit(
                owner_wallet_address=owner_wallet_address,
                amount_base_units=amount_base_units,
                prepared_transaction_base64=prepared.transaction_base64,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        return replace(prepared, sponsor_deposit_id=sponsor_deposit_id)

    async def sponsor_vault_deposit(self, request: SponsorVaultDepositRequest) -> VaultBalance:
        self._validate_wallet_address(request.owner_wallet_address)
        async with self._sponsored_deposit_lock:
            intent = self._sponsored_deposit_intents.pop(request.sponsor_deposit_id, None)
        if intent is None or intent.expires_at < datetime.now(UTC):
            raise StateConflictError(
                "가스리스 예치 요청이 만료되었거나 이미 처리되었습니다. 다시 시도해 주세요."
            )
        if intent.owner_wallet_address != request.owner_wallet_address:
            raise StateConflictError("가스리스 예치 요청의 지갑 주소가 일치하지 않습니다.")
        result = await self._solana.sponsor_vault_deposit(
            owner_wallet_address=intent.owner_wallet_address,
            amount_base_units=intent.amount_base_units,
            prepared_transaction_base64=intent.prepared_transaction_base64,
            signed_transaction_base64=request.signed_transaction_base64,
            reference_id=f"gasless-deposit-{request.sponsor_deposit_id[:20]}",
        )
        return await self.confirm_vault_deposit(
            ConfirmVaultDepositRequest(
                owner_wallet_address=intent.owner_wallet_address,
                amount_usdc=base_units_to_usdc(intent.amount_base_units),
                signature=result.signature,
            )
        )

    async def confirm_vault_deposit(self, request: ConfirmVaultDepositRequest) -> VaultBalance:
        self._validate_wallet_address(request.owner_wallet_address)
        if not await self._solana.verify_vault_deposit(
            signature=request.signature,
            owner_wallet_address=request.owner_wallet_address,
            amount_base_units=usdc_to_base_units(request.amount_usdc),
        ):
            raise StateConflictError("Agent Vault 예치 트랜잭션을 확인하지 못했습니다.")
        if not self._repository.claim_deposit(request.signature):
            return self.get_vault(request.owner_wallet_address)
        current = self.get_vault(request.owner_wallet_address)
        updated = current.model_copy(
            update={
                "available_usdc": current.available_usdc + request.amount_usdc,
                "available_base_units": base_units_string(
                    int(current.available_base_units)
                    + usdc_to_base_units(request.amount_usdc)
                ),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        self._repository.save_vault(updated)
        return updated

    async def request_verification(
        self,
        invoice_id: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            self.assert_invoice_access(invoice, identity)
            if invoice.verification_id is not None:
                return self._copy_invoice(invoice)
            if invoice.status is not InvoiceStatus.DOCUMENT_REVIEW_REQUIRED:
                raise StateConflictError(
                    "DOCUMENT_REVIEW_REQUIRED 상태에서만 Buyer 검증을 요청할 수 있습니다."
                )
            async with self._sequence_lock:
                self._verification_sequence += 1
                verification_id = (
                    f"VER-{datetime.now(UTC).year}-{str(self._verification_sequence).zfill(3)}"
                )
            requested_at = datetime.now(UTC).isoformat()
            verification = Verification(
                id=verification_id,
                invoice_id=invoice_id,
                status=VerificationStatus.PENDING,
                created_at=requested_at,
            )
            self._verifications[verification_id] = verification
            invoice.verification_id = verification_id
            invoice.verification_requested_at = requested_at
            invoice.status = InvoiceStatus.BUYER_REVIEW
            self._repository.save_verification(verification)
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    def list_verifications(
        self,
        identity: AuthenticatedIdentity | None = None,
    ) -> list[Verification]:
        return [
            verification.model_copy(deep=True)
            for verification in sorted(
                self._verifications.values(),
                key=lambda item: item.id,
                reverse=True,
            )
            if self._can_access_invoice(self._invoice(verification.invoice_id), identity)
        ]

    def get_verification(
        self,
        verification_id: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> Verification:
        verification = self._verification(verification_id)
        self.assert_invoice_access(self._invoice(verification.invoice_id), identity)
        return verification.model_copy(deep=True)

    async def confirm_verification(
        self,
        verification_id: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        verification = self._verification(verification_id)
        async with self._invoice_lock(verification.invoice_id):
            invoice = self._invoice(verification.invoice_id)
            self.assert_invoice_access(invoice, identity)
            if verification.status is VerificationStatus.CONFIRMED:
                return self._copy_invoice(invoice)
            if (
                verification.status is not VerificationStatus.PENDING
                or invoice.status is not InvoiceStatus.BUYER_REVIEW
            ):
                raise StateConflictError("현재 상태에서는 Buyer 검증을 확정할 수 없습니다.")

            agent_analysis = self._agent_analyses[invoice.id]
            try:
                valuation = value_invoice_in_usdc(
                    invoice_amount=invoice.invoice_amount,
                    currency=invoice.currency,
                )
            except ValueError as exc:
                raise StateConflictError(
                    "RWA 발행은 현재 USD 또는 USDC 인보이스만 USDC 기준으로 산정할 수 있습니다."
                ) from exc
            verification.status = VerificationStatus.CONFIRMED
            verification.responded_at = datetime.now(UTC).isoformat()
            invoice.verification_confirmed_at = datetime.now(UTC).isoformat()
            invoice.status = InvoiceStatus.RISK_ASSESSING
            hard_gate = self._evaluate_hard_gate(invoice, verification)
            if not hard_gate.passed:
                invoice.risk_passport = RiskPassport(
                    invoice_id=invoice.id,
                    eligibility="BLOCKED",
                    risk_score=None,
                    positive_factors=[],
                    risk_factors=[
                        RiskFactor(severity="HIGH", title="Hard Gate 실패", description=reason)
                        for reason in hard_gate.failure_reasons
                    ],
                    hard_gate=hard_gate,
                    data_coverage_bps=10_000,
                    policy_version="hard-gate-v1",
                    generated_at=datetime.now(UTC).isoformat(),
                )
                invoice.status = InvoiceStatus.BLOCKED
                self._repository.save_verification(verification)
                self._save_invoice(invoice)
                return self._copy_invoice(invoice)

            remaining_term_days = max(
                0, (self._parse_iso_date(invoice.due_date, "인보이스 만기일") - date.today()).days
            )
            score_result = self._risk_scoring.evaluate(
                RiskScoringRequest(
                    invoice_id=invoice.id,
                    face_value_base_units=valuation.face_value_base_units,
                    has_document_mismatches=bool(agent_analysis.mismatches),
                    buyer_confirmed=True,
                    remaining_term_days=remaining_term_days,
                    document_summary="mismatch" if agent_analysis.mismatches else "documents consistent",
                    buyer_key=invoice.buyer.id or invoice.buyer.name,
                    supplier_key=invoice.supplier.id or invoice.supplier.name,
                )
            )
            pricing = calculate_dynamic_pricing(
                face_value_base_units=valuation.face_value_base_units,
                remaining_term_days=remaining_term_days,
                risk_score=score_result.score,
                policy=self._pricing_policy,
            )
            advance_amount = pricing.supplier_expected_settlement_usdc if pricing else None
            advance_base_units = pricing.supplier_settlement_base_units if pricing else None
            decision = RiskDecision(
                score=score_result.score,
                level=score_result.eligibility.value,
                eligibility=score_result.eligibility,
                advance_rate_bps=(
                    advance_base_units * 10_000 // valuation.face_value_base_units
                    if advance_base_units is not None and valuation.face_value_base_units
                    else None
                ),
                advance_amount_usdc=advance_amount,
            )
            risk_request = self._risk_request(invoice, agent_analysis, decision)
            try:
                risk_result = await self._agents.analyze_risk(risk_request)
            except AgentError as exc:
                invoice.status = InvoiceStatus.ERROR
                raise IntegrationError(f"Gemini Risk 설명 생성에 실패했습니다: {exc}") from exc

            reasons = {
                reason.factor_code: reason.explanation for reason in risk_result.risk_reasons
            }
            positive_codes = {"BUYER_CONFIRMED", "DOCUMENT_CONSISTENCY"}
            early_terms = (
                EarlySettlementTerms(
                    face_value_usdc=pricing.face_value_usdc,
                    face_value_base_units=base_units_string(pricing.face_value_base_units),
                    discount_amount_usdc=pricing.face_value_usdc
                    - pricing.supplier_expected_settlement_usdc,
                    discount_rate_bps=(
                        (pricing.face_value_base_units - pricing.supplier_settlement_base_units)
                        * 10_000
                        // pricing.face_value_base_units
                        if pricing.face_value_base_units
                        else 0
                    ),
                    investor_required_return_usdc=pricing.expected_investor_return_usdc,
                    platform_fee_usdc=pricing.platform_fee_usdc,
                    platform_fee_base_units=base_units_string(pricing.platform_fee_base_units),
                    reserve_amount_usdc=0,
                    reserve_rate_bps=0,
                    initial_advance_usdc=pricing.supplier_expected_settlement_usdc,
                    expected_reserve_return_usdc=0,
                    expected_final_proceeds_usdc=pricing.supplier_expected_settlement_usdc,
                    remaining_term_days=pricing.remaining_term_days,
                    sofr_rate_bps=pricing.sofr_bps,
                    sofr_as_of=pricing.sofr_as_of,
                    sofr_source=pricing.sofr_source,
                    buyer_risk_score=pricing.buyer_risk_score,
                    risk_spread_bps=pricing.buyer_risk_spread_bps,
                    country_legal_spread_bps=pricing.country_legal_spread_bps,
                    annual_expected_yield_bps=pricing.investor_net_annual_yield_bps,
                    platform_fee_share_bps=pricing.platform_fee_share_bps,
                    expected_investor_return_usdc=pricing.expected_investor_return_usdc,
                    investor_net_return_base_units=base_units_string(
                        pricing.investor_net_return_base_units
                    ),
                    investor_settlement_usdc=pricing.investor_settlement_usdc,
                    investor_settlement_base_units=base_units_string(
                        pricing.investor_settlement_base_units
                    ),
                    purchase_amount_usdc=pricing.purchase_amount_usdc,
                    purchase_amount_base_units=base_units_string(
                        pricing.purchase_amount_base_units
                    ),
                    supplier_expected_settlement_usdc=pricing.supplier_expected_settlement_usdc,
                    supplier_settlement_base_units=base_units_string(
                        pricing.supplier_settlement_base_units
                    ),
                )
                if pricing is not None
                else None
            )
            invoice.risk_passport = RiskPassport(
                invoice_id=invoice.id,
                eligibility=decision.eligibility,
                risk_score=decision.score,
                positive_factors=[
                    PositiveFactor(
                        title=factor.title,
                        description=reasons[factor.code],
                    )
                    for factor in risk_request.risk_factors
                    if factor.code in positive_codes
                ],
                risk_factors=[
                    RiskFactor(
                        severity=("HIGH" if factor.code == "DOCUMENT_MISMATCH" else "LOW"),
                        title=factor.title,
                        description=reasons[factor.code],
                    )
                    for factor in risk_request.risk_factors
                    if factor.code not in positive_codes
                ],
                suggested_advance_rate_bps=decision.advance_rate_bps,
                suggested_advance_amount_usdc=decision.advance_amount_usdc,
                suggested_advance_base_units=(
                    base_units_string(advance_base_units) if advance_base_units is not None else None
                ),
                invoice_face_value_usdc=valuation.face_value_usdc,
                invoice_face_value_base_units=base_units_string(valuation.face_value_base_units),
                source_currency_to_usdc_rate=valuation.source_currency_to_usdc_rate,
                data_coverage_bps=score_result.data_coverage_bps,
                score_factors=[
                    RiskScoreFactor(
                        key=factor.key,
                        label=factor.label,
                        score=factor.score,
                        max_score=factor.max_score,
                        source=factor.source,
                        detail=factor.detail,
                        synthetic=factor.synthetic,
                    )
                    for factor in score_result.factors
                ],
                hard_gate=hard_gate,
                early_settlement_terms=early_terms,
                model_name=self._agents.model_name,
                policy_version=score_result.method_version,
                generated_at=datetime.now(UTC).isoformat(),
            )
            invoice.status = (
                InvoiceStatus.OFFER_READY
                if score_result.eligibility.value == "ELIGIBLE" and pricing is not None
                else InvoiceStatus.BLOCKED
            )
            self._append_trace(
                invoice,
                source="RISK_AGENT",
                target="TREASURY_AGENT",
                status="COMPLETED",
                summary=risk_result.risk_passport.summary,
            )
            self._record_completed_agent_run(
                invoice_id=invoice.id,
                trigger=AgentTrigger.BUYER_CONFIRMED,
                tool_name="evaluate_risk",
                summary=f"Risk Score {score_result.score} ({score_result.method_version})를 산출했습니다.",
                source_agent="RISK_AGENT",
                target_agent="TREASURY_AGENT",
            )
            self._repository.save_verification(verification)
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    async def request_risk_review(
        self,
        invoice_id: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        """Pause the offer flow while the supplier's Risk Score appeal is reviewed."""

        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            self.assert_invoice_access(invoice, identity)
            if invoice.status is InvoiceStatus.REVIEW_REQUESTED:
                return self._copy_invoice(invoice)
            if invoice.status not in {
                InvoiceStatus.OFFER_READY,
                InvoiceStatus.REJECTED,
                InvoiceStatus.BLOCKED,
            }:
                raise StateConflictError(
                    "거절, Hard Gate 실패 또는 Risk Score 산정 이후에만 이의 신청을 제출할 수 있습니다."
                )

            invoice.status = InvoiceStatus.REVIEW_REQUESTED
            invoice.review_requested_at = datetime.now(UTC).isoformat()
            self._append_trace(
                invoice,
                source="RISK_AGENT",
                target="RISK_AGENT",
                status="SUBMITTED",
                summary="공급기업이 Risk Score 이의 신청을 제출했습니다.",
            )
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    async def reject_verification(
        self,
        verification_id: str,
        *,
        reason_code: str,
        detail: str | None,
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        verification = self._verification(verification_id)
        async with self._invoice_lock(verification.invoice_id):
            invoice = self._invoice(verification.invoice_id)
            self.assert_invoice_access(invoice, identity)
            if identity is not None and identity.source != "DEMO" and identity.role is not LoginRole.BUYER:
                raise StateConflictError("구매기업만 인보이스 확인을 거절할 수 있습니다.")
            if verification.status is VerificationStatus.REJECTED:
                return self._copy_invoice(invoice)
            if verification.status is not VerificationStatus.PENDING or invoice.status is not InvoiceStatus.BUYER_REVIEW:
                raise StateConflictError("구매기업 검토 중인 인보이스만 거절할 수 있습니다.")

            now = datetime.now(UTC).isoformat()
            verification.status = VerificationStatus.REJECTED
            verification.rejection_reason_code = reason_code
            verification.rejection_reason_detail = detail
            verification.responded_at = now
            invoice.status = InvoiceStatus.REJECTED
            invoice.verification_rejected_at = now
            invoice.rejection_reason_code = reason_code
            invoice.rejection_reason_detail = detail
            self._append_trace(
                invoice,
                source="DOCUMENT_AGENT",
                target="RISK_AGENT",
                status="FAILED",
                summary=f"구매기업이 인보이스 확인을 거절했습니다: {reason_code}",
            )
            self._repository.save_verification(verification)
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    async def respond_to_offer(
        self,
        invoice_id: str,
        response: OfferResponse,
        identity: AuthenticatedIdentity | None = None,
    ) -> tuple[Invoice, bool]:
        """Issue one RWA unit and then queue automatic mandate evaluation."""

        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            self.assert_invoice_access(invoice, identity)
            if response is OfferResponse.ACCEPT and invoice.status in {
                InvoiceStatus.RWA_ISSUED,
                InvoiceStatus.FUNDING,
                InvoiceStatus.FUNDED,
            }:
                return self._copy_invoice(invoice), False
            if response is OfferResponse.DECLINE and invoice.status is InvoiceStatus.BLOCKED:
                return self._copy_invoice(invoice), False
            if invoice.status is not InvoiceStatus.OFFER_READY:
                raise StateConflictError(
                    "OFFER_READY 상태에서만 조기정산 조건에 응답할 수 있습니다."
                )
            if response is OfferResponse.DECLINE:
                invoice.status = InvoiceStatus.BLOCKED
                self._save_invoice(invoice)
                return self._copy_invoice(invoice), False

            supplier_wallet = (
                identity.wallet_address
                if identity is not None and identity.source == "PRIVY"
                else self._repository.get_supplier_wallet() or invoice.supplier.wallet_address
            )
            if not supplier_wallet or supplier_wallet.startswith("DEMO_"):
                if self._solana.mode != "mock":
                    raise StateConflictError("RWA 발행 전 공급기업 정산 지갑을 연결해 주세요.")
                supplier_wallet = "DEMO_SUPPLIER_WALLET"
            if self._solana.mode != "mock":
                self._validate_wallet_address(supplier_wallet)
            invoice.supplier.wallet_address = supplier_wallet
            issued = await self._solana.issue_rwa(invoice_id=invoice.id)
            asset = RwaAsset(
                invoice_id=invoice.id,
                mint_address=issued.mint_address,
                escrow_token_account=issued.escrow_token_account,
                status="ISSUED",
                issue_transaction=self._transaction(
                    result=issued.transaction,
                    amount_base_units=0,
                    to_address=issued.escrow_token_account,
                ),
                face_value_usdc=invoice.risk_passport.invoice_face_value_usdc if invoice.risk_passport else None,
                face_value_base_units=(
                    invoice.risk_passport.invoice_face_value_base_units
                    if invoice.risk_passport
                    else None
                ),
                issuance_price_usdc=(
                    invoice.risk_passport.suggested_advance_amount_usdc if invoice.risk_passport else None
                ),
                issuance_price_base_units=(
                    invoice.risk_passport.suggested_advance_base_units
                    if invoice.risk_passport
                    else None
                ),
                purchase_price_usdc=(
                    invoice.risk_passport.suggested_advance_amount_usdc
                    if invoice.risk_passport
                    else None
                ),
                purchase_price_base_units=(
                    invoice.risk_passport.suggested_advance_base_units
                    if invoice.risk_passport
                    else None
                ),
            )
            self._repository.save_rwa_asset(asset)
            invoice.rwa_asset = asset
            invoice.status = InvoiceStatus.RWA_ISSUED
            self._append_trace(
                invoice,
                source="TREASURY_AGENT",
                target="TREASURY_AGENT",
                status="COMPLETED",
                summary="인보이스별 RWA 1개를 Devnet 에스크로에 발행했습니다.",
            )
            self._record_completed_agent_run(
                invoice_id=invoice.id,
                trigger=AgentTrigger.OFFER_ACCEPTED,
                tool_name="evaluate_mandate",
                summary="RWA를 발행하고 Mandate 평가 대기 상태로 전환했습니다.",
                source_agent="TREASURY_AGENT",
                target_agent="TREASURY_AGENT",
            )
            self._save_invoice(invoice)
            return self._copy_invoice(invoice), True

    async def execute_mandated_investment(self, invoice_id: str) -> None:
        """Evaluate all active mandates and atomically buy the issued RWA when eligible."""

        if not self._repository.claim_execution(invoice_id):
            return
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            asset = self._repository.get_rwa_asset(invoice_id)
            if invoice.status is not InvoiceStatus.RWA_ISSUED or asset is None:
                self._repository.finish_execution(invoice_id, "FAILED")
                return
            invoice.rwa_asset = asset
            candidates = self._repository.active_mandates()
            if not candidates:
                decision = AgentDecision(
                    invoice_id=invoice_id,
                    status="PENDING",
                    checks={"activeMandate": False},
                    reason="활성화된 투자 Mandate를 기다리고 있습니다.",
                    created_at=datetime.now(UTC).isoformat(),
                )
                self._repository.save_decision(decision)
                invoice.agent_decision = decision
                self._save_invoice(invoice)
                self._repository.finish_execution(invoice_id, "WAITING")
                return

            approved: tuple[InvestorMandate, VaultBalance, AgentDecision] | None = None
            for mandate in candidates:
                vault = self.get_vault(mandate.owner_wallet_address)
                decision = self._evaluate_mandate(invoice, mandate, vault)
                self._repository.save_decision(decision)
                invoice.agent_decision = decision
                if decision.status == "APPROVED":
                    approved = (mandate, vault, decision)
                    break
            if approved is None:
                self._save_invoice(invoice)
                self._repository.finish_execution(invoice_id, "WAITING")
                return

            mandate, vault, decision = approved
            invoice.status = InvoiceStatus.FUNDING
            self._append_trace(
                invoice,
                source="TREASURY_AGENT",
                target="SETTLEMENT_AGENT",
                status="WORKING",
                summary="Mandate 기준을 통과해 Agent Vault 자동 매수를 실행합니다.",
            )
            amount_base_units = int(decision.amount_base_units)
            try:
                result = await self._solana.purchase_rwa(
                    invoice_id=invoice.id,
                    rwa_mint_address=asset.mint_address,
                    escrow_token_account=asset.escrow_token_account,
                    supplier_wallet_address=invoice.supplier.wallet_address or "",
                    amount_base_units=amount_base_units,
                )
            except IntegrationError as exc:
                invoice.status = InvoiceStatus.ERROR
                failed = decision.model_copy(
                    update={
                        "status": "FAILED",
                        "reason": "Devnet 자동 매수 트랜잭션에 실패했습니다.",
                    }
                )
                self._repository.save_decision(failed)
                invoice.agent_decision = failed
                self._save_invoice(invoice)
                self._repository.finish_execution(invoice_id, "FAILED")
                logger.error("RWA automatic purchase failed for %s: %s", invoice.id, exc)
                return

            invoice.funding_transaction = self._transaction(
                result=result,
                amount_base_units=amount_base_units,
                to_address=invoice.supplier.wallet_address or "",
            )
            if result.status is TransactionStatus.CONFIRMED:
                sold_asset = asset.model_copy(
                    update={
                        "status": "SOLD",
                        "purchase_transaction": invoice.funding_transaction,
                        "owner_vault_address": vault.vault_address,
                        "owner_wallet_address": mandate.owner_wallet_address,
                    }
                )
                completed = decision.model_copy(update={"status": "EXECUTED"})
                self._repository.save_rwa_asset(sold_asset)
                self._repository.save_decision(completed)
                self._repository.save_vault(
                    vault.model_copy(
                        update={
                            "available_usdc": base_units_to_usdc(
                                int(vault.available_base_units) - amount_base_units
                            ),
                            "available_base_units": base_units_string(
                                int(vault.available_base_units) - amount_base_units
                            ),
                            "updated_at": datetime.now(UTC).isoformat(),
                        }
                    )
                )
                invoice.rwa_asset = sold_asset
                invoice.agent_decision = completed
                invoice.status = InvoiceStatus.FUNDED
                self._append_trace(
                    invoice,
                    source="TREASURY_AGENT",
                    target="SETTLEMENT_AGENT",
                    status="COMPLETED",
                    summary=(
                        "Agent Vault가 RWA를 자동 매수하고 공급기업 지갑에 USDC를 지급했습니다."
                    ),
                )
                self._save_invoice(invoice)
                self._repository.finish_execution(invoice_id, "COMPLETED")
            else:
                self._save_invoice(invoice)
                self._repository.finish_execution(invoice_id, "WAITING")

    async def execute_pending_investments(self) -> None:
        """Re-evaluate issued RWAs after a Mandate or Vault balance changes."""

        await asyncio.gather(
            *(
                self.execute_mandated_investment(invoice.id)
                for invoice in self._invoices.values()
                if invoice.status is InvoiceStatus.RWA_ISSUED
            )
        )

    def get_agent_activity(self, invoice_id: str, *, role: Literal["Supplier", "Investor"]):
        """Return persisted records only; sensitive mandate/vault fields stay server-side."""
        invoice = self._invoice(invoice_id)
        runs = self._repository.list_agent_runs(invoice_id)
        items: list[AgentActivityItem] = []
        for run in runs:
            items.append(
                AgentActivityItem(
                    id=run.id,
                    kind="RUN",
                    status=run.status.value,
                    title="자동 업무 진행" if role == "Supplier" else "Orchestrator 실행",
                    summary=run.plan_summary,
                    created_at=run.created_at,
                    method_version=(invoice.risk_passport.policy_version if role == "Investor" else None),
                )
            )
            for call in self._repository.list_agent_tool_calls(run.id):
                items.append(
                    AgentActivityItem(
                        id=call.id,
                        kind="TOOL",
                        status=call.status.value,
                        title=("업무 단계 완료" if role == "Supplier" else call.tool_name),
                        summary=call.output_summary,
                        created_at=call.completed_at or call.started_at or run.created_at,
                        method_version=(invoice.risk_passport.policy_version if role == "Investor" else None),
                    )
                )
        if role == "Investor" and invoice.agent_decision is not None:
            decision = invoice.agent_decision
            tx = invoice.funding_transaction
            items.append(
                AgentActivityItem(
                    id=f"decision-{invoice.id}",
                    kind="TOOL",
                    status=decision.status,
                    title="Mandate 정책 검사",
                    summary=decision.reason or "Mandate 정책 검사를 완료했습니다.",
                    created_at=decision.created_at,
                    checks=decision.checks,
                    transaction_signature=tx.signature if tx else None,
                    explorer_url=tx.explorer_url if tx else None,
                )
            )
        return AgentActivityTimeline(
            invoice_id=invoice_id,
            role=role,
            runs=runs,
            timeline=sorted(items, key=lambda item: item.created_at),
        )

    async def settle_mock_payment(
        self,
        invoice_id: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        if not self._settings.mock_settlement_enabled:
            raise StateConflictError(
                "Mock 상환 정산은 현재 GCP 자동매수 범위에서 비활성화되어 있습니다."
            )
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            self.assert_invoice_access(invoice, identity)
            if invoice.status is InvoiceStatus.SETTLED:
                return self._copy_invoice(invoice)
            if invoice.status not in {
                InvoiceStatus.FUNDED,
                InvoiceStatus.REPAYMENT_PENDING,
                InvoiceStatus.SETTLING,
                InvoiceStatus.SETTLEMENT_FAILED,
            }:
                raise StateConflictError("펀딩 완료 후에만 Mock 입금과 정산을 처리할 수 있습니다.")

            face_value_base_units = self._invoice_face_value_base_units(invoice)
            signature = str(
                Signature.from_bytes(
                    hashlib.sha512(f"buyer-payment-{invoice.id}".encode()).digest()
                )
            )
            settlement_wallet = await self._solana.settlement_wallet_address()
            invoice.buyer_payment_transaction = BlockchainTransaction(
                signature=signature,
                status=TransactionStatus.CONFIRMED,
                amount_usdc=base_units_to_usdc(face_value_base_units),
                amount_base_units=base_units_string(face_value_base_units),
                from_address=invoice.buyer.wallet_address or "DEMO_BUYER_WALLET",
                to_address=settlement_wallet,
                explorer_url=f"https://explorer.solana.com/tx/{signature}?cluster=devnet",
                created_at=datetime.now(UTC).isoformat(),
                sandbox=True,
                provider="MOCK",
            )
            invoice.buyer_paid_at = datetime.now(UTC).isoformat()
            await self._run_settlement(invoice)
            return self._copy_invoice(invoice)

    async def prepare_buyer_payment(
        self,
        invoice_id: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> BuyerPaymentPreparation:
        invoice = self._invoice(invoice_id)
        self.assert_invoice_access(invoice, identity)
        if identity is not None and identity.source != "DEMO" and identity.role is not LoginRole.BUYER:
            raise StateConflictError("구매기업만 만기 USDC 결제를 준비할 수 있습니다.")
        if invoice.status not in {
            InvoiceStatus.FUNDED,
            InvoiceStatus.REPAYMENT_PENDING,
            InvoiceStatus.SETTLING,
            InvoiceStatus.SETTLEMENT_FAILED,
        }:
            raise StateConflictError("펀딩 완료된 인보이스만 만기 결제를 진행할 수 있습니다.")
        today = date.today()
        due_date = self._parse_iso_date(invoice.due_date, "인보이스 만기일")
        bypass = self._settings.mock_settlement_enabled
        if today < due_date and not bypass:
            raise StateConflictError("인보이스 만기일부터 결제를 진행할 수 있습니다.")
        buyer_wallet = identity.wallet_address if identity and identity.wallet_address else invoice.buyer.wallet_address
        if not buyer_wallet:
            raise StateConflictError("구매기업 Embedded Wallet을 찾을 수 없습니다.")
        invoice.buyer.wallet_address = buyer_wallet
        face_value_base_units = self._invoice_face_value_base_units(invoice)
        face_value = base_units_to_usdc(face_value_base_units)
        decimals = self._settings.solana_usdc_decimals
        transfers: list[BuyerPaymentTransfer]
        if self._solana.mode == "direct":
            terms = invoice.risk_passport.early_settlement_terms if invoice.risk_passport else None
            investor_wallet = invoice.rwa_asset.owner_wallet_address if invoice.rwa_asset else None
            if terms is None or not investor_wallet:
                raise StateConflictError("RWA 보유 투자자 지갑과 정산 조건을 찾을 수 없습니다.")
            platform_fee_base_units = int(terms.platform_fee_base_units)
            investor_base_units = face_value_base_units - platform_fee_base_units
            transfers = [
                BuyerPaymentTransfer(
                    recipient_wallet_address=investor_wallet,
                    amount_usdc=base_units_to_usdc(investor_base_units),
                    amount_base_units=base_units_string(investor_base_units),
                )
            ]
            if platform_fee_base_units > 0:
                transfers.append(
                    BuyerPaymentTransfer(
                        recipient_wallet_address=self._settings.platform_fee_wallet_address,
                        amount_usdc=terms.platform_fee_usdc,
                        amount_base_units=base_units_string(platform_fee_base_units),
                    )
                )
        else:
            settlement_wallet = await self._solana.settlement_wallet_address()
            transfers = [
                BuyerPaymentTransfer(
                    recipient_wallet_address=settlement_wallet,
                    amount_usdc=face_value,
                    amount_base_units=base_units_string(face_value_base_units),
                )
            ]
        return BuyerPaymentPreparation(
            invoice_id=invoice.id,
            buyer_wallet_address=buyer_wallet,
            settlement_wallet_address=transfers[0].recipient_wallet_address,
            usdc_mint_address=self._solana.stablecoin_mint_address,
            amount_usdc=face_value,
            amount_base_units=base_units_string(face_value_base_units),
            decimals=decimals,
            due_date=invoice.due_date,
            transfers=transfers,
            demo_due_date_bypass=bypass and today < due_date,
        )

    async def confirm_buyer_payment(
        self,
        invoice_id: str,
        *,
        signature: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> Invoice:
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            self.assert_invoice_access(invoice, identity)
            if invoice.status is InvoiceStatus.SETTLED:
                if invoice.buyer_payment_transaction and invoice.buyer_payment_transaction.signature == signature:
                    return self._copy_invoice(invoice)
                raise StateConflictError("이미 정산 완료된 인보이스입니다.")
            for other in self._invoices.values():
                if (
                    other.id != invoice.id
                    and other.buyer_payment_transaction is not None
                    and other.buyer_payment_transaction.signature == signature
                ):
                    raise StateConflictError("이미 다른 인보이스에 사용된 결제 트랜잭션입니다.")
            if invoice.buyer_payment_transaction is not None:
                if invoice.buyer_payment_transaction.signature != signature:
                    raise StateConflictError("다른 결제 트랜잭션이 이미 확인되었습니다.")
                await self._run_settlement(invoice)
                return self._copy_invoice(invoice)

            preparation = await self.prepare_buyer_payment(invoice_id, identity)
            verified = all(
                await asyncio.gather(
                    *(
                        self._solana.verify_usdc_payment(
                            signature=signature,
                            sender_wallet_address=preparation.buyer_wallet_address,
                            recipient_wallet_address=transfer.recipient_wallet_address,
                            amount_base_units=int(transfer.amount_base_units),
                        )
                        for transfer in preparation.transfers
                    )
                )
            )
            if not verified:
                raise StateConflictError(
                    "USDC 결제 트랜잭션의 보내는 지갑, 수령 지갑, Mint 또는 금액이 일치하지 않습니다."
                )
            provider = "PRIVY" if self._solana.mode == "privy" else "DIRECT" if self._solana.mode == "direct" else "MOCK"
            invoice.buyer_payment_transaction = BlockchainTransaction(
                signature=signature,
                status=TransactionStatus.CONFIRMED,
                amount_usdc=preparation.transfers[0].amount_usdc,
                amount_base_units=preparation.transfers[0].amount_base_units,
                from_address=preparation.buyer_wallet_address,
                to_address=preparation.transfers[0].recipient_wallet_address,
                explorer_url=f"https://explorer.solana.com/tx/{signature}?cluster=devnet",
                created_at=datetime.now(UTC).isoformat(),
                sandbox=self._solana.mode == "mock",
                provider=provider,
            )
            invoice.buyer_paid_at = datetime.now(UTC).isoformat()
            invoice.status = InvoiceStatus.SETTLING
            self._save_invoice(invoice)
            await self._run_settlement(invoice)
            return self._copy_invoice(invoice)

    async def _run_settlement(self, invoice: Invoice) -> None:
        terms = invoice.risk_passport.early_settlement_terms if invoice.risk_passport else None
        if terms is None:
            raise StateConflictError("영속화된 조기정산 가격 정보를 찾을 수 없습니다.")
        if invoice.buyer_payment_transaction is None:
            raise StateConflictError("구매기업 USDC 결제가 먼저 확인되어야 합니다.")
        face_value_base_units = int(terms.face_value_base_units)
        platform_fee_base_units = int(terms.platform_fee_base_units)
        investor_base_units = face_value_base_units - platform_fee_base_units
        face_value = base_units_to_usdc(face_value_base_units)
        platform_fee = base_units_to_usdc(platform_fee_base_units)
        investor_amount = base_units_to_usdc(investor_base_units)
        invoice.status = InvoiceStatus.SETTLING
        if self._solana.mode == "direct":
            investor_wallet = invoice.rwa_asset.owner_wallet_address if invoice.rwa_asset else None
            if not investor_wallet:
                raise StateConflictError("RWA 보유 투자자 지갑을 찾을 수 없습니다.")
            if invoice.investor_payout_transaction is None:
                invoice.investor_payout_transaction = invoice.buyer_payment_transaction.model_copy(
                    update={
                        "amount_usdc": investor_amount,
                        "amount_base_units": base_units_string(investor_base_units),
                        "to_address": investor_wallet,
                    }
                )
                invoice.settlement_transaction = invoice.investor_payout_transaction
                self._save_invoice(invoice)
            if platform_fee_base_units > 0 and invoice.platform_fee_transaction is None:
                invoice.platform_fee_transaction = invoice.buyer_payment_transaction.model_copy(
                    update={
                        "amount_usdc": platform_fee,
                        "amount_base_units": base_units_string(platform_fee_base_units),
                        "to_address": self._settings.platform_fee_wallet_address,
                    }
                )
                self._save_invoice(invoice)
        else:
            investor_wallet = (
                invoice.rwa_asset.owner_wallet_address
                if invoice.rwa_asset and invoice.rwa_asset.owner_wallet_address
                else invoice.rwa_asset.owner_vault_address
                if invoice.rwa_asset and invoice.rwa_asset.owner_vault_address
                else self._settings.investor_settlement_wallet_address
            )
            settlement_wallet_id = self._settings.privy_settlement_wallet_id or "MOCK_SETTLEMENT"
            try:
                if invoice.investor_payout_transaction is None:
                    result = await self._solana.send_usdc(
                        wallet_id=settlement_wallet_id,
                        transfers=[
                            ChainTransfer(
                                to_address=investor_wallet,
                                amount_base_units=investor_base_units,
                            )
                        ],
                        reference_id=f"investor-payout-{invoice.id}",
                    )
                    invoice.investor_payout_transaction = self._transaction(
                        result=result,
                        amount_base_units=investor_base_units,
                        to_address=investor_wallet,
                    )
                    invoice.settlement_transaction = invoice.investor_payout_transaction
                    self._save_invoice(invoice)
                if platform_fee_base_units > 0 and invoice.platform_fee_transaction is None:
                    result = await self._solana.send_usdc(
                        wallet_id=settlement_wallet_id,
                        transfers=[
                            ChainTransfer(
                                to_address=self._settings.platform_fee_wallet_address,
                                amount_base_units=platform_fee_base_units,
                            )
                        ],
                        reference_id=f"platform-fee-{invoice.id}",
                    )
                    invoice.platform_fee_transaction = self._transaction(
                        result=result,
                        amount_base_units=platform_fee_base_units,
                        to_address=self._settings.platform_fee_wallet_address,
                    )
                    self._save_invoice(invoice)
            except IntegrationError:
                invoice.status = InvoiceStatus.SETTLEMENT_FAILED
                self._save_invoice(invoice)
                raise

        if (
            invoice.investor_payout_transaction
            and invoice.investor_payout_transaction.status is TransactionStatus.CONFIRMED
            and (platform_fee_base_units == 0 or (
                invoice.platform_fee_transaction
                and invoice.platform_fee_transaction.status is TransactionStatus.CONFIRMED
            ))
        ):
            invoice.settlement = Settlement(
                invoice_face_value_usdc=face_value,
                invoice_face_value_base_units=base_units_string(face_value_base_units),
                investor_settlement_usdc=investor_amount,
                investor_settlement_base_units=base_units_string(investor_base_units),
                platform_fee_usdc=platform_fee,
                platform_fee_base_units=base_units_string(platform_fee_base_units),
                supplier_residual_usdc=0,
                supplier_residual_base_units="0",
            )
            invoice.status = InvoiceStatus.SETTLED
            if invoice.rwa_asset is not None:
                invoice.rwa_asset = invoice.rwa_asset.model_copy(update={"status": "SETTLED"})
                self._repository.save_rwa_asset(invoice.rwa_asset)
            self._append_trace(
                invoice,
                source="SETTLEMENT_AGENT",
                target="SETTLEMENT_AGENT",
                status="COMPLETED",
                summary="구매기업 USDC 결제 확인과 투자자·플랫폼 정산을 완료했습니다.",
            )
            self._save_invoice(invoice)

    @staticmethod
    def _invoice_face_value_base_units(invoice: Invoice) -> int:
        value = (
            invoice.risk_passport.invoice_face_value_base_units
            if invoice.risk_passport
            else None
        )
        if value is None or int(value) <= 0:
            raise StateConflictError("확정된 인보이스 USDC 액면가를 찾을 수 없습니다.")
        return int(value)

    def investor_dashboard(
        self,
        identity: AuthenticatedIdentity | None = None,
    ) -> InvestorDashboard:
        active = {
            InvoiceStatus.FUNDED,
            InvoiceStatus.REPAYMENT_PENDING,
            InvoiceStatus.SETTLING,
        }
        active_invoices_with_passport = [
            invoice
            for invoice in self._invoices.values()
            if invoice.status in active and invoice.risk_passport is not None
        ]
        outstanding = sum(
            invoice.risk_passport.suggested_advance_amount_usdc or 0
            for invoice in active_invoices_with_passport
        )
        today = date.today()
        due_within_30_days = sum(
            invoice.risk_passport.suggested_advance_amount_usdc or 0
            for invoice in active_invoices_with_passport
            if (due_date := self._try_parse_iso_date(invoice.due_date)) is not None
            and 0 <= (due_date - today).days <= 30
        )
        traces = sorted(
            (trace for invoice in self._invoices.values() for trace in invoice.agent_traces),
            key=lambda trace: trace.created_at,
            reverse=True,
        )[:20]
        mandates = self._repository.active_mandates()
        if identity is not None and identity.source == "PRIVY":
            mandates = [
                mandate
                for mandate in mandates
                if mandate.owner_wallet_address == identity.wallet_address
            ]
        vault = self.get_vault(mandates[0].owner_wallet_address) if mandates else None
        attention_required_statuses = {InvoiceStatus.ERROR, InvoiceStatus.BLOCKED}
        attention_required_count = 0
        for invoice in self._invoices.values():
            if invoice.status in attention_required_statuses:
                attention_required_count += 1
                continue
            decision = self._repository.get_decision(invoice.id)
            if decision is not None and decision.status == "FAILED":
                attention_required_count += 1
        return InvestorDashboard(
            investor_name=(
                identity.company_name if identity and identity.company_name else "Nova Capital"
            ),
            automated_investment_active=bool(mandates),
            mandate_status="ACTIVE" if mandates else "DRAFT",
            available_vault_usdc=vault.available_usdc if vault else 0,
            outstanding_principal_usdc=outstanding,
            due_within_30_days_usdc=due_within_30_days,
            attention_required_count=attention_required_count,
            recent_agent_traces=[trace.model_copy(deep=True) for trace in traces],
        )

    async def close(self) -> None:
        await self._solana.aclose()
        self._repository.close()

    @property
    def settings(self) -> BackendSettings:
        return self._settings

    @property
    def repository(self) -> RwaRepository:
        return self._repository

    async def _reserve_invoice_ids(self, document_count: int) -> tuple[str, list[str]]:
        async with self._sequence_lock:
            self._invoice_sequence += 1
            invoice_id = f"INV-{datetime.now(UTC).year}-{str(self._invoice_sequence).zfill(3)}"
            document_ids = []
            for _ in range(document_count):
                self._document_sequence += 1
                document_ids.append(f"DOC-{str(self._document_sequence).zfill(3)}")
        return invoice_id, document_ids

    def _validate_uploads(self, uploads: list[UploadedDocument]) -> None:
        supplied_types = [upload.type for upload in uploads]
        if len(supplied_types) != len(set(supplied_types)):
            raise DocumentValidationError("문서별 파일은 정확히 1개만 허용합니다.")
        missing = REQUIRED_DOCUMENT_TYPES - set(supplied_types)
        if missing:
            raise DocumentValidationError(
                "필수 파일이 누락되었습니다: "
                + ", ".join(sorted(document.value for document in missing))
            )
        for upload in uploads:
            if upload.mime_type not in ALLOWED_MIME_TYPES:
                raise DocumentValidationError(
                    f"{upload.type.value} 파일은 PDF, JPG, JPEG, PNG만 허용합니다."
                )
            if not upload.data:
                raise DocumentValidationError(f"{upload.type.value} 파일이 비어 있습니다.")
            if len(upload.data) > self._settings.max_document_size_bytes:
                raise DocumentValidationError(
                    f"{upload.type.value} 파일은 20MB를 초과할 수 없습니다."
                )

    def _to_frontend_analysis(
        self,
        invoice_id: str,
        result: DocumentAnalysisResult,
        document_types: dict[str, DocumentType],
    ) -> DocumentAnalysis:
        mismatch_fields = {mismatch.field.value for mismatch in result.mismatches}

        def field(
            attribute: str,
            alias: str,
            converter: Callable[[object], object] | None = None,
            preferred_types: tuple[DocumentType, ...] = (),
        ) -> dict[str, object]:
            preference = {document_type: index for index, document_type in enumerate(preferred_types)}
            ordered_documents = sorted(
                result.documents,
                key=lambda document: preference.get(
                    document_types[document.document_id],
                    len(preference),
                ),
            )
            for document in ordered_documents:
                value = getattr(document.extracted_data, attribute)
                if value is None:
                    continue
                try:
                    converted = converter(value) if converter is not None else value
                except (TypeError, ValueError):
                    return {
                        "value": None,
                        "status": ExtractedFieldStatus.REVIEW_REQUIRED,
                    }
                source = next(
                    (evidence for evidence in document.source_evidence if evidence.field == alias),
                    None,
                )
                evidence_dto = (
                    {
                        "document_type": document_types[document.document_id],
                        "page": source.page,
                        "text": source.quote,
                    }
                    if source is not None
                    else None
                )
                return {
                    "value": converted,
                    "evidence": evidence_dto,
                    "status": (
                        ExtractedFieldStatus.MISMATCH
                        if alias in mismatch_fields
                        else ExtractedFieldStatus.MATCHED
                    ),
                }
            return {"value": None, "status": ExtractedFieldStatus.MISSING}

        return DocumentAnalysis(
            invoice_id=invoice_id,
            status=AnalysisStatus.COMPLETED,
            invoice_number=field(
                "invoice_number", "invoiceNumber", preferred_types=(DocumentType.INVOICE,)
            ),
            supplier_name=field(
                "supplier_name", "supplierName", preferred_types=(DocumentType.INVOICE,)
            ),
            buyer_name=field(
                "buyer_name", "buyerName", preferred_types=(DocumentType.INVOICE,)
            ),
            amount=field(
                "total_amount",
                "totalAmount",
                self._parse_amount,
                (DocumentType.INVOICE, DocumentType.PURCHASE_ORDER),
            ),
            currency=field(
                "currency", "currency", preferred_types=(DocumentType.INVOICE,)
            ),
            due_date=field("due_date", "dueDate", preferred_types=(DocumentType.INVOICE,)),
            contract_number=field(
                "contract_number",
                "contractNumber",
                preferred_types=(DocumentType.CONTRACT, DocumentType.INVOICE),
            ),
            purchase_order_number=field(
                "purchase_order_number",
                "purchaseOrderNumber",
                preferred_types=(
                    DocumentType.PURCHASE_ORDER,
                    DocumentType.INVOICE,
                    DocumentType.DELIVERY_PROOF,
                ),
            ),
            delivery_completed=field(
                "delivery_completed",
                "deliveryCompleted",
                preferred_types=(DocumentType.DELIVERY_PROOF, DocumentType.INVOICE),
            ),
            model_name=self._agents.model_name,
            prompt_version="document-agent.v1",
            analyzed_at=datetime.now(UTC).isoformat(),
        )

    def _apply_extracted_metadata(
        self,
        invoice: Invoice,
        result: DocumentAnalysisResult,
    ) -> None:
        analysis = invoice.analysis
        if analysis is None:
            return
        if analysis.amount.value is not None:
            invoice.invoice_amount = analysis.amount.value
        if analysis.currency.value is not None:
            invoice.currency = analysis.currency.value
        if analysis.due_date.value is not None:
            invoice.due_date = analysis.due_date.value
        if analysis.contract_number.value is not None:
            invoice.contract_number = analysis.contract_number.value
        if analysis.purchase_order_number.value is not None:
            invoice.purchase_order_number = analysis.purchase_order_number.value
        if analysis.supplier_name.value is not None:
            invoice.supplier.name = analysis.supplier_name.value
        buyer_name = analysis.buyer_name.value
        if buyer_name:
            invoice.buyer.name = buyer_name
            buyer_company = self._repository.find_company_by_name(buyer_name, "BUYER")
            if buyer_company is not None:
                invoice.buyer.id = buyer_company.id
                invoice.buyer.name = buyer_company.name
        issue_date = self._first_raw_value(result, "issue_date")
        if isinstance(issue_date, str):
            invoice.issue_date = issue_date

    def _risk_request(
        self,
        invoice: Invoice,
        analysis: DocumentAnalysisResult,
        decision: RiskDecision,
    ) -> RiskAnalysisRequest:
        source_evidence = [
            evidence for document in analysis.documents for evidence in document.source_evidence
        ]
        buyer_evidence = SourceEvidence(
            evidence_id=f"{invoice.id}-buyer-confirmed",
            document_id=invoice.id,
            page=1,
            field="buyerDecision",
            quote="Buyer confirmed",
        )
        source_evidence.append(buyer_evidence)
        evidence_ids = [item.evidence_id for item in source_evidence[:3]]
        factors = [
            RiskFactorContext(
                code="BUYER_CONFIRMED",
                title="구매기업 검증 완료",
                facts=["구매기업이 거래와 지급 의무를 확정했습니다."],
                source_evidence_ids=[buyer_evidence.evidence_id],
            ),
            RiskFactorContext(
                code=("DOCUMENT_MISMATCH" if analysis.mismatches else "DOCUMENT_CONSISTENCY"),
                title=("문서 불일치 검토 필요" if analysis.mismatches else "핵심 문서 조건 일치"),
                facts=[
                    (
                        "제출 문서 사이에 불일치가 존재합니다."
                        if analysis.mismatches
                        else "제출 문서의 핵심 거래 조건이 일치합니다."
                    )
                ],
                source_evidence_ids=evidence_ids or [buyer_evidence.evidence_id],
            ),
            RiskFactorContext(
                code="LIMITED_HISTORY",
                title="단일 Demo 거래",
                facts=["현재 MVP의 단일 거래 이력을 기준으로 평가합니다."],
                source_evidence_ids=[buyer_evidence.evidence_id],
            ),
        ]
        return RiskAnalysisRequest(
            invoice_id=invoice.id,
            buyer_decision="CONFIRM",
            risk_score=decision.score,
            risk_level=decision.level,
            risk_factors=factors,
            source_evidence=source_evidence,
        )

    @staticmethod
    def _transaction(
        *,
        result: ChainTransferResult,
        amount_base_units: int,
        to_address: str,
    ) -> BlockchainTransaction:
        return BlockchainTransaction(
            signature=result.signature,
            status=result.status,
            amount_usdc=base_units_to_usdc(amount_base_units),
            amount_base_units=base_units_string(amount_base_units),
            from_address=result.from_address,
            to_address=to_address,
            explorer_url=(f"https://explorer.solana.com/tx/{result.signature}?cluster=devnet"),
            created_at=datetime.now(UTC).isoformat(),
            sandbox=result.sandbox,
            provider=result.provider,
        )

    def _append_trace(
        self,
        invoice: Invoice,
        *,
        source: TraceSource,
        target: TraceTarget,
        status: TraceStatus,
        summary: str,
    ) -> None:
        self._trace_sequence += 1
        now = datetime.now(UTC).isoformat()
        invoice.agent_traces.append(
            AgentTrace(
                id=f"TRACE-{str(self._trace_sequence).zfill(4)}",
                invoice_id=invoice.id,
                source_agent=source,
                target_agent=target,
                status=status,
                summary=summary,
                created_at=now,
                completed_at=now if status in {"COMPLETED", "FAILED"} else None,
            )
        )

    def _record_completed_agent_run(
        self,
        *,
        invoice_id: str,
        trigger: AgentTrigger,
        tool_name: str,
        summary: str,
        source_agent: str,
        target_agent: str,
    ) -> None:
        """Persist redacted activity. Never place prompts, documents, keys or wallet data here."""
        now = datetime.now(UTC).isoformat()
        run_id = f"RUN-{secrets.token_urlsafe(12)}"
        run = AgentRun(
            id=run_id,
            invoice_id=invoice_id,
            trigger=trigger,
            status=AgentRunStatus.COMPLETED,
            plan_summary=summary,
            created_at=now,
            started_at=now,
            completed_at=now,
        )
        self._repository.save_agent_run(run)
        self._repository.save_agent_tool_call(
            AgentToolCall(
                id=f"CALL-{secrets.token_urlsafe(12)}",
                run_id=run_id,
                sequence=1,
                tool_name=tool_name,
                status=ToolCallStatus.COMPLETED,
                input_summary="invoice_id only",
                output_summary=summary,
                started_at=now,
                completed_at=now,
            )
        )
        self._repository.save_agent_handoff(
            AgentHandoff(
                id=f"HANDOFF-{secrets.token_urlsafe(12)}",
                run_id=run_id,
                source_agent=source_agent,
                target_agent=target_agent,
                reason=summary,
                status=ToolCallStatus.COMPLETED,
                created_at=now,
                completed_at=now,
            )
        )

    def assert_invoice_access(
        self,
        invoice: Invoice,
        identity: AuthenticatedIdentity | None,
    ) -> None:
        if not self._can_access_invoice(invoice, identity):
            raise NotFoundError(f"Invoice {invoice.id}를 찾을 수 없습니다.")

    def _evaluate_hard_gate(
        self,
        invoice: Invoice,
        verification: Verification,
    ):
        matches = self._matching_prior_invoice_numbers(invoice)
        supplier = self._repository.get_company(invoice.supplier.id)
        buyer = self._repository.get_company(invoice.buyer.id)

        def company_active(company) -> bool:
            # Legacy/demo invoices predate persisted company profiles. They remain
            # eligible; registered companies must be active and not failed/rejected.
            if company is None:
                return True
            return company.status == "ACTIVE" and company.kyb_status not in {
                "FAILED",
                "REJECTED",
                "NOT_VERIFIED",
            }

        return evaluate_hard_gate(
            HardGateInput(
                buyer_confirmed=verification.status is VerificationStatus.CONFIRMED,
                supplier_verified=company_active(supplier),
                buyer_verified=company_active(buyer),
                delivery_completed=bool(
                    invoice.analysis
                    and invoice.analysis.delivery_completed.value is True
                ),
                dispute_free=verification.status is not VerificationStatus.DISPUTED,
                duplicate_free=not matches,
                not_overdue=self._parse_iso_date(invoice.due_date, "인보이스 만기일") >= date.today(),
                prior_assignment_free=not any(other.rwa_asset is not None for other in matches),
                # External sanctions data is explicitly out of MVP scope. The
                # adapter supplies a deterministic clear result until integrated.
                sanctions_clear=True,
            )
        )

    def _matching_prior_invoice_numbers(self, invoice: Invoice) -> list[Invoice]:
        invoice_number = (
            invoice.analysis.invoice_number.value
            if invoice.analysis is not None
            else None
        )
        if not invoice_number:
            return []
        invoice_sequence = self._max_id_suffix([invoice.id], "INV-")
        return [
            other
            for other in self._invoices.values()
            if other.id != invoice.id
            and self._max_id_suffix([other.id], "INV-") < invoice_sequence
            and other.analysis is not None
            and other.analysis.invoice_number.value == invoice_number
        ]

    def _ensure_dynamic_pricing(self, invoice: Invoice) -> None:
        passport = invoice.risk_passport
        if passport is None or passport.risk_score is None:
            return
        terms = passport.early_settlement_terms
        complete_fields = (
            "remaining_term_days",
            "sofr_rate_bps",
            "sofr_as_of",
            "sofr_source",
            "buyer_risk_score",
            "risk_spread_bps",
            "country_legal_spread_bps",
            "annual_expected_yield_bps",
            "platform_fee_share_bps",
            "expected_investor_return_usdc",
            "investor_net_return_base_units",
            "investor_settlement_usdc",
            "investor_settlement_base_units",
            "purchase_amount_usdc",
            "purchase_amount_base_units",
            "supplier_expected_settlement_usdc",
            "supplier_settlement_base_units",
        )
        remaining_term_days = max(
            0,
            (
                self._parse_iso_date(invoice.due_date, "인보이스 만기일")
                - datetime.now(BUSINESS_TIMEZONE).date()
            ).days,
        )
        terms_are_complete = terms is not None and all(
            getattr(terms, field) is not None for field in complete_fields
        )
        # Pricing is an immutable quote once the Offer is created.  This method
        # exists only to backfill legacy/incomplete local demo records.
        if terms_are_complete:
            return

        face_value_base_units = passport.invoice_face_value_base_units
        if face_value_base_units is None and terms is not None:
            face_value_base_units = terms.face_value_base_units
        if face_value_base_units is None:
            return

        pricing = calculate_dynamic_pricing(
            face_value_base_units=int(face_value_base_units),
            remaining_term_days=remaining_term_days,
            risk_score=passport.risk_score,
            policy=self._pricing_policy,
        )
        if pricing is None:
            return

        discount_base_units = (
            pricing.face_value_base_units - pricing.supplier_settlement_base_units
        )
        discount_amount = base_units_to_usdc(discount_base_units)
        refreshed_terms = EarlySettlementTerms(
            face_value_usdc=pricing.face_value_usdc,
            face_value_base_units=base_units_string(pricing.face_value_base_units),
            discount_amount_usdc=discount_amount,
            discount_rate_bps=(
                discount_base_units * 10_000 // pricing.face_value_base_units
                if pricing.face_value_base_units
                else 0
            ),
            investor_required_return_usdc=pricing.expected_investor_return_usdc,
            platform_fee_usdc=pricing.platform_fee_usdc,
            platform_fee_base_units=base_units_string(pricing.platform_fee_base_units),
            reserve_amount_usdc=0,
            reserve_rate_bps=0,
            initial_advance_usdc=pricing.supplier_expected_settlement_usdc,
            expected_reserve_return_usdc=0,
            expected_final_proceeds_usdc=pricing.supplier_expected_settlement_usdc,
            remaining_term_days=pricing.remaining_term_days,
            sofr_rate_bps=pricing.sofr_bps,
            sofr_as_of=pricing.sofr_as_of,
            sofr_source=pricing.sofr_source,
            buyer_risk_score=pricing.buyer_risk_score,
            risk_spread_bps=pricing.buyer_risk_spread_bps,
            country_legal_spread_bps=pricing.country_legal_spread_bps,
            annual_expected_yield_bps=pricing.investor_net_annual_yield_bps,
            platform_fee_share_bps=pricing.platform_fee_share_bps,
            expected_investor_return_usdc=pricing.expected_investor_return_usdc,
            investor_net_return_base_units=base_units_string(
                pricing.investor_net_return_base_units
            ),
            investor_settlement_usdc=pricing.investor_settlement_usdc,
            investor_settlement_base_units=base_units_string(
                pricing.investor_settlement_base_units
            ),
            purchase_amount_usdc=pricing.purchase_amount_usdc,
            purchase_amount_base_units=base_units_string(pricing.purchase_amount_base_units),
            supplier_expected_settlement_usdc=pricing.supplier_expected_settlement_usdc,
            supplier_settlement_base_units=base_units_string(
                pricing.supplier_settlement_base_units
            ),
        )
        invoice.risk_passport = passport.model_copy(
            update={
                "suggested_advance_amount_usdc": pricing.supplier_expected_settlement_usdc,
                "suggested_advance_base_units": base_units_string(
                    pricing.supplier_settlement_base_units
                ),
                "suggested_advance_rate_bps": (
                    pricing.supplier_settlement_base_units
                    * 10_000
                    // pricing.face_value_base_units
                    if pricing.face_value_base_units
                    else 0
                ),
                "early_settlement_terms": refreshed_terms,
            }
        )
        self._save_invoice(invoice)

    def _reconcile_buyer_invoices(
        self,
        identity: AuthenticatedIdentity | None,
    ) -> None:
        if (
            identity is None
            or identity.source != "PRIVY"
            or identity.role is not LoginRole.BUYER
            or identity.company_id is None
            or not identity.company_name
        ):
            return

        company_name = identity.company_name.strip().casefold()
        for invoice in self._invoices.values():
            if (
                invoice.buyer.id != identity.company_id
                and invoice.buyer.name.strip().casefold() == company_name
            ):
                invoice.buyer = invoice.buyer.model_copy(
                    update={"id": identity.company_id}
                )
                self._save_invoice(invoice)

    def assert_wallet_ownership(
        self,
        wallet_address: str,
        identity: AuthenticatedIdentity | None,
    ) -> None:
        if (
            identity is not None
            and identity.source == "PRIVY"
            and identity.wallet_address != wallet_address
        ):
            raise StateConflictError(
                "가입한 Privy Embedded Wallet과 요청 지갑 주소가 일치하지 않습니다."
            )

    @staticmethod
    def _can_access_invoice(
        invoice: Invoice,
        identity: AuthenticatedIdentity | None,
    ) -> bool:
        if identity is None or identity.source == "DEMO":
            return True
        if identity.role is LoginRole.INVESTOR:
            return True
        if identity.company_id is None:
            return False
        if identity.role is LoginRole.SUPPLIER:
            return invoice.supplier.id == identity.company_id
        if identity.role is LoginRole.BUYER:
            return invoice.buyer.id == identity.company_id
        return False

    def _invoice(self, invoice_id: str) -> Invoice:
        try:
            return self._invoices[invoice_id]
        except KeyError as exc:
            raise NotFoundError(f"Invoice {invoice_id}를 찾을 수 없습니다.") from exc

    def _verification(self, verification_id: str) -> Verification:
        try:
            return self._verifications[verification_id]
        except KeyError as exc:
            raise NotFoundError(f"Verification {verification_id}를 찾을 수 없습니다.") from exc

    def _invoice_lock(self, invoice_id: str) -> asyncio.Lock:
        return self._invoice_locks.setdefault(invoice_id, asyncio.Lock())

    def _copy_invoice(self, invoice: Invoice) -> Invoice:
        copy = invoice.model_copy(deep=True)
        copy.documents = [
            document.model_copy(update={"storage_url": self._storage.presentation_url(document)})
            for document in copy.documents
        ]
        copy.rwa_asset = self._repository.get_rwa_asset(invoice.id)
        copy.agent_decision = self._repository.get_decision(invoice.id)
        return copy

    def _evaluate_mandate(
        self, invoice: Invoice, mandate: InvestorMandate, vault: VaultBalance
    ) -> AgentDecision:
        passport = invoice.risk_passport
        amount = passport.suggested_advance_amount_usdc if passport else None
        amount_base_units = (
            int(passport.suggested_advance_base_units)
            if passport and passport.suggested_advance_base_units is not None
            else None
        )
        due_date = self._parse_iso_date(invoice.due_date, "인보이스 만기일")
        remaining_days = max(0, (due_date - date.today()).days)
        policy = mandate.policy
        is_policy_active = self._parse_iso_date(policy.expires_at, "Mandate 만료일") >= date.today()
        is_minimum_risk_score = bool(
            passport
            and passport.risk_score is not None
            and passport.risk_score >= policy.minimum_risk_score
        )
        is_total_investment_within_limit = bool(
            amount_base_units is not None
            and self._repository.committed_base_units_for_mandate(mandate.id) + amount_base_units
            <= usdc_to_base_units(policy.total_investment_limit_usdc)
        )
        registered_buyer = self._repository.get_company(invoice.buyer.id)
        mandate_buyer_name = (
            registered_buyer.name if registered_buyer is not None else invoice.buyer.name
        )
        checks = {
            "policyActive": is_policy_active,
            "riskEligible": bool(passport and passport.eligibility.value == "ELIGIBLE"),
            "minimumRiskScore": is_minimum_risk_score,
            "buyerAllowlist": mandate_buyer_name in policy.buyer_allowlist,
            "maximumRemainingTerm": remaining_days <= policy.maximum_remaining_term_days,
            "perInvoiceLimit": bool(
                amount_base_units is not None
                and amount_base_units <= usdc_to_base_units(policy.per_invoice_limit_usdc)
            ),
            "totalInvestmentLimit": is_total_investment_within_limit,
            "vaultAvailableBalance": bool(
                amount_base_units is not None
                and int(vault.available_base_units) >= amount_base_units
            ),
        }
        rejected = [name for name, passed in checks.items() if not passed]
        return AgentDecision(
            invoice_id=invoice.id,
            mandate_id=mandate.id,
            status="APPROVED" if not rejected else "REJECTED",
            checks=checks,
            amount_usdc=amount or 0,
            amount_base_units=(
                base_units_string(amount_base_units) if amount_base_units is not None else "0"
            ),
            reason=None if not rejected else f"Mandate 기준 미충족: {', '.join(rejected)}",
            created_at=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def _canonical_mandate_message(owner_wallet_address: str, policy: MandatePolicy) -> str:
        payload = {
            "domain": "InvoiceX AP2 Mandate",
            "version": 1,
            "ownerWalletAddress": owner_wallet_address,
            "policy": policy.model_dump(by_alias=True, mode="json"),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _parse_iso_date(value: str, label: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise StateConflictError(f"{label} 형식이 올바르지 않습니다.") from exc

    @staticmethod
    def _try_parse_iso_date(value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _validate_wallet_address(wallet_address: str) -> None:
        try:
            Pubkey.from_string(wallet_address)
        except ValueError as exc:
            raise StateConflictError("유효한 Solana 지갑 주소가 필요합니다.") from exc

    @staticmethod
    def _parse_amount(value: object) -> Decimal:
        normalized = re.sub(r"[,_\s]", "", str(value)).strip()
        return parse_usdc(normalized)

    @staticmethod
    def _first_raw_value(
        result: DocumentAnalysisResult,
        attribute: str,
    ) -> object | None:
        return next(
            (
                value
                for document in result.documents
                if (value := getattr(document.extracted_data, attribute)) is not None
            ),
            None,
        )
