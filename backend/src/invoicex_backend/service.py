"""Invoice aggregate service and state-transition orchestration."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal

from invoicex_agents.exceptions import AgentError
from invoicex_agents.models.common import SourceEvidence
from invoicex_agents.models.document import DocumentAnalysisResult
from invoicex_agents.models.risk import RiskAnalysisRequest, RiskFactorContext

from invoicex_backend.agents import AgentDocument, AgentGateway
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import (
    DocumentValidationError,
    IntegrationError,
    NotFoundError,
    StateConflictError,
)
from invoicex_backend.models import (
    AgentTrace,
    AnalysisStatus,
    BlockchainTransaction,
    ChainTransfer,
    ChainTransferResult,
    DocumentAnalysis,
    DocumentType,
    ExtractedFieldStatus,
    InvestorDashboard,
    Invoice,
    InvoiceParty,
    InvoiceStatus,
    OfferResponse,
    PositiveFactor,
    RiskFactor,
    RiskPassport,
    Settlement,
    TransactionStatus,
    UploadedDocument,
    Verification,
    VerificationStatus,
)
from invoicex_backend.policy import (
    DeterministicRiskPolicy,
    RiskDecision,
    TreasuryMandatePolicy,
)
from invoicex_backend.seed import load_seed_documents
from invoicex_backend.solana import SolanaGateway
from invoicex_backend.state_store import JsonStateStore, PersistedState
from invoicex_backend.storage import LocalDocumentStorage

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = frozenset(
    {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
)
REQUIRED_DOCUMENT_TYPES = frozenset(DocumentType)
TraceSource = Literal[
    "DOCUMENT_AGENT",
    "RISK_AGENT",
    "TREASURY_AGENT",
    "SETTLEMENT_AGENT",
]
TraceTarget = Literal["RISK_AGENT", "TREASURY_AGENT", "SETTLEMENT_AGENT"]
TraceStatus = Literal["SUBMITTED", "WORKING", "COMPLETED", "FAILED"]
TRANSIENT_STATUS_AGENTS: dict[InvoiceStatus, TraceSource] = {
    InvoiceStatus.DOCUMENT_ANALYZING: "DOCUMENT_AGENT",
    InvoiceStatus.RISK_ASSESSING: "RISK_AGENT",
    InvoiceStatus.FUNDING: "TREASURY_AGENT",
    InvoiceStatus.SETTLING: "SETTLEMENT_AGENT",
}
TRANSIENT_STATUSES = frozenset(TRANSIENT_STATUS_AGENTS)


class InvoiceService:
    """Own Invoice state and coordinate Agent and chain adapters."""

    def __init__(
        self,
        *,
        settings: BackendSettings,
        agent_gateway: AgentGateway,
        solana_gateway: SolanaGateway,
        storage: LocalDocumentStorage,
        state_store: JsonStateStore,
    ) -> None:
        self._settings = settings
        self._agents = agent_gateway
        self._solana = solana_gateway
        self._storage = storage
        self._state_store = state_store
        self._risk_policy = DeterministicRiskPolicy()
        self._mandate_policy = TreasuryMandatePolicy(settings)
        self._invoice_locks: dict[str, asyncio.Lock] = {}
        self._sequence_lock = asyncio.Lock()
        self._persist_lock = asyncio.Lock()
        self._reset_lock = asyncio.Lock()

        restored = state_store.load()
        self._invoices: dict[str, Invoice] = restored.invoices
        self._agent_analyses: dict[str, DocumentAnalysisResult] = (
            restored.agent_analyses
        )
        self._verifications: dict[str, Verification] = restored.verifications
        self._invoice_sequence = restored.invoice_sequence
        self._verification_sequence = restored.verification_sequence
        self._document_sequence = restored.document_sequence
        self._trace_sequence = restored.trace_sequence
        self._pending_documents: dict[str, list[AgentDocument]] = {}
        self._recover_interrupted_work()

    def _recover_interrupted_work(self) -> None:
        """Fail invoices whose in-flight work died with the previous process.

        The Gemini and chain calls are not resumable, and the frontend polls
        transient statuses forever, so a restart must not leave one behind.
        """

        interrupted = [
            invoice
            for invoice in self._invoices.values()
            if invoice.status in TRANSIENT_STATUSES
        ]
        if not interrupted:
            return
        for invoice in interrupted:
            logger.error(
                "재시작으로 중단된 작업을 ERROR로 정리합니다: %s (%s)",
                invoice.id,
                invoice.status.value,
            )
            self._append_trace(
                invoice,
                source=TRANSIENT_STATUS_AGENTS[invoice.status],
                target="SETTLEMENT_AGENT",
                status="FAILED",
                summary=(
                    f"서버 재시작으로 {invoice.status.value} 처리가 중단되었습니다."
                ),
            )
            invoice.status = InvoiceStatus.ERROR
        self._state_store.save(self._snapshot())

    def _new_invoice(self, invoice_id: str, status: InvoiceStatus) -> Invoice:
        """Build the demo Invoice shell before the Document Agent fills it in."""

        now = datetime.now(UTC)
        invoice_number = int(invoice_id[-3:])
        return Invoice(
            id=invoice_id,
            supplier=InvoiceParty(
                id="SUPPLIER_ALPHA",
                name="Alpha Components",
                wallet_address=self._settings.supplier_wallet_address,
            ),
            buyer=InvoiceParty(id="BUYER_PRIME", name="Prime Mobility"),
            investor=InvoiceParty(
                id="INVESTOR_NOVA",
                name="Nova Capital",
                vault_address=self._settings.investor_settlement_wallet_address,
            ),
            invoice_amount_krw=20_000_000,
            issue_date=now.date().isoformat(),
            due_date=(now + timedelta(days=90)).date().isoformat(),
            delivery_date=(now - timedelta(days=5)).date().isoformat(),
            contract_number=f"PM-SUPPLY-{now.year}-04",
            purchase_order_number=f"PO-{89340 + invoice_number}",
            status=status,
            verification_id=None,
            documents=[],
            analysis=None,
            risk_passport=None,
            funding_transaction=None,
            settlement_transaction=None,
            settlement=None,
            agent_traces=[],
        )

    async def reset_demo(self) -> Invoice:
        """Drop every invoice and hand back a fresh DRAFT one, as the mock adapter does."""

        async with self._reset_lock:
            self._invoices.clear()
            self._verifications.clear()
            self._agent_analyses.clear()
            # Dropping the pending bytes makes any in-flight background analysis
            # a no-op instead of mutating the reseeded invoice.
            self._pending_documents.clear()
            self._invoice_locks.clear()
            async with self._sequence_lock:
                self._invoice_sequence = 0
                self._verification_sequence = 0
                self._document_sequence = 0
                self._trace_sequence = 0
            await asyncio.to_thread(self._storage.clear)

            invoice_id, _ = await self._reserve_invoice_ids(0)
            invoice = self._new_invoice(invoice_id, InvoiceStatus.DRAFT)
            self._invoices[invoice_id] = invoice
            await self._persist()
            return self._copy_invoice(invoice)

    async def analyze_seeded_documents(self, invoice_id: str) -> Invoice:
        """Attach the demo seed documents to a DRAFT invoice and analyze them.

        The DemoControlPage runs this instead of an upload, so a demo can be
        replayed without re-picking four files.
        """

        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            if invoice.status is not InvoiceStatus.DRAFT:
                raise StateConflictError(
                    "DRAFT 상태에서만 시드 문서를 분석할 수 있습니다."
                )
            uploads = await asyncio.to_thread(
                load_seed_documents,
                self._settings.resolved_seed_directory(),
            )
            self._validate_uploads(uploads)
            document_ids = await self._reserve_document_ids(len(uploads))
            try:
                stored = await asyncio.gather(
                    *[
                        self._storage.store(
                            document_id=document_id,
                            invoice_id=invoice_id,
                            upload=upload,
                        )
                        for document_id, upload in zip(
                            document_ids, uploads, strict=True
                        )
                    ]
                )
            except OSError as exc:
                invoice.status = InvoiceStatus.ERROR
                await self._persist()
                raise IntegrationError("시드 문서를 저장하지 못했습니다.") from exc

            invoice.documents = list(stored)
            invoice.status = InvoiceStatus.DOCUMENT_ANALYZING
            self._pending_documents[invoice_id] = [
                AgentDocument(
                    document_id=document_id,
                    type=upload.type,
                    mime_type=upload.mime_type,
                    data=upload.data,
                )
                for document_id, upload in zip(document_ids, uploads, strict=True)
            ]
            await self._persist()
            return self._copy_invoice(invoice)

    async def create_invoice(self, uploads: list[UploadedDocument]) -> Invoice:
        self._validate_uploads(uploads)
        invoice_id, document_ids = await self._reserve_invoice_ids(len(uploads))
        invoice = self._new_invoice(invoice_id, InvoiceStatus.DOCUMENT_ANALYZING)
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
        except OSError as exc:
            invoice.status = InvoiceStatus.ERROR
            await self._persist()
            raise IntegrationError("업로드 문서를 저장하지 못했습니다.") from exc

        invoice.documents = list(stored_documents)
        # Hold the bytes in memory so the background analysis does not have to
        # read them back from storage. They are deliberately never persisted.
        self._pending_documents[invoice_id] = [
            AgentDocument(
                document_id=document_id,
                type=upload.type,
                mime_type=upload.mime_type,
                data=upload.data,
            )
            for document_id, upload in zip(document_ids, uploads, strict=True)
        ]
        await self._persist()
        return self._copy_invoice(invoice)

    async def complete_document_analysis(self, invoice_id: str) -> None:
        """Run the Document Agent outside the upload request.

        The frontend already polls DOCUMENT_ANALYZING, so returning the invoice
        immediately keeps a multi-document Gemini call off the request path.
        """

        async with self._invoice_lock(invoice_id):
            invoice = self._invoices.get(invoice_id)
            agent_documents = self._pending_documents.pop(invoice_id, None)
            if invoice is None or agent_documents is None:
                return
            if invoice.status is not InvoiceStatus.DOCUMENT_ANALYZING:
                return

            try:
                agent_result = await self._agents.analyze_documents(
                    invoice_id,
                    agent_documents,
                )
            except AgentError as exc:
                invoice.status = InvoiceStatus.ERROR
                self._append_trace(
                    invoice,
                    source="DOCUMENT_AGENT",
                    target="RISK_AGENT",
                    status="FAILED",
                    summary=f"Gemini 문서 분석에 실패했습니다: {exc}",
                )
                logger.error("Document analysis failed for %s: %s", invoice_id, exc)
                await self._persist()
                return

            self._agent_analyses[invoice_id] = agent_result
            invoice.analysis = self._to_frontend_analysis(
                invoice_id,
                agent_result,
                {document.document_id: document.type for document in agent_documents},
            )
            self._apply_extracted_metadata(invoice, agent_result)
            invoice.status = InvoiceStatus.DOCUMENT_REVIEW_REQUIRED
            self._append_trace(
                invoice,
                source="DOCUMENT_AGENT",
                target="RISK_AGENT",
                status="COMPLETED",
                summary="Gemini 문서 분석과 근거 연결을 완료했습니다.",
            )
            await self._persist()

    def list_invoices(self) -> list[Invoice]:
        return [
            self._copy_invoice(invoice)
            for invoice in sorted(
                self._invoices.values(),
                key=lambda item: item.id,
                reverse=True,
            )
        ]

    def get_invoice(self, invoice_id: str) -> Invoice:
        return self._copy_invoice(self._invoice(invoice_id))

    async def request_verification(self, invoice_id: str) -> Invoice:
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            if invoice.verification_id is not None:
                return self._copy_invoice(invoice)
            if invoice.status is not InvoiceStatus.DOCUMENT_REVIEW_REQUIRED:
                raise StateConflictError(
                    "DOCUMENT_REVIEW_REQUIRED 상태에서만 Buyer 검증을 요청할 수 있습니다."
                )
            async with self._sequence_lock:
                self._verification_sequence += 1
                verification_id = (
                    f"VER-{datetime.now(UTC).year}-"
                    f"{str(self._verification_sequence).zfill(3)}"
                )
            verification = Verification(
                id=verification_id,
                invoice_id=invoice_id,
                status=VerificationStatus.PENDING,
            )
            self._verifications[verification_id] = verification
            invoice.verification_id = verification_id
            invoice.status = InvoiceStatus.BUYER_REVIEW
            await self._persist()
            return self._copy_invoice(invoice)

    def list_verifications(self) -> list[Verification]:
        return [
            verification.model_copy(deep=True)
            for verification in sorted(
                self._verifications.values(),
                key=lambda item: item.id,
                reverse=True,
            )
        ]

    def get_verification(self, verification_id: str) -> Verification:
        return self._verification(verification_id).model_copy(deep=True)

    async def confirm_verification(self, verification_id: str) -> Invoice:
        verification = self._verification(verification_id)
        async with self._invoice_lock(verification.invoice_id):
            invoice = self._invoice(verification.invoice_id)
            if verification.status is VerificationStatus.CONFIRMED:
                return self._copy_invoice(invoice)
            if (
                verification.status is not VerificationStatus.PENDING
                or invoice.status is not InvoiceStatus.BUYER_REVIEW
            ):
                raise StateConflictError("현재 상태에서는 Buyer 검증을 확정할 수 없습니다.")

            verification.status = VerificationStatus.CONFIRMED
            invoice.status = InvoiceStatus.RISK_ASSESSING
            await self._persist()
            return self._copy_invoice(invoice)

    async def complete_risk_assessment(self, invoice_id: str) -> None:
        """Build the Risk Passport outside the Buyer confirm request.

        The frontend already polls RISK_ASSESSING, so the Gemini explanation
        call does not need to block the Buyer's request.
        """

        async with self._invoice_lock(invoice_id):
            invoice = self._invoices.get(invoice_id)
            if invoice is None or invoice.status is not InvoiceStatus.RISK_ASSESSING:
                return
            agent_analysis = self._agent_analyses.get(invoice_id)
            if agent_analysis is None:
                invoice.status = InvoiceStatus.ERROR
                self._append_trace(
                    invoice,
                    source="RISK_AGENT",
                    target="TREASURY_AGENT",
                    status="FAILED",
                    summary="문서 분석 결과가 없어 Risk Passport를 만들 수 없습니다.",
                )
                logger.error("Missing document analysis for %s", invoice_id)
                await self._persist()
                return

            decision = self._risk_policy.evaluate(
                has_mismatches=bool(agent_analysis.mismatches),
                face_value_usdc=invoice.invoice_amount_krw // 1_000,
            )
            risk_request = self._risk_request(invoice, agent_analysis, decision)
            try:
                risk_result = await self._agents.analyze_risk(risk_request)
            except AgentError as exc:
                invoice.status = InvoiceStatus.ERROR
                self._append_trace(
                    invoice,
                    source="RISK_AGENT",
                    target="TREASURY_AGENT",
                    status="FAILED",
                    summary=f"Gemini Risk 설명 생성에 실패했습니다: {exc}",
                )
                logger.error("Risk assessment failed for %s: %s", invoice_id, exc)
                await self._persist()
                return

            reasons = {
                reason.factor_code: reason.explanation
                for reason in risk_result.risk_reasons
            }
            positive_codes = {"BUYER_CONFIRMED", "DOCUMENT_CONSISTENCY"}
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
                        severity=(
                            "HIGH" if factor.code == "DOCUMENT_MISMATCH" else "LOW"
                        ),
                        title=factor.title,
                        description=reasons[factor.code],
                    )
                    for factor in risk_request.risk_factors
                    if factor.code not in positive_codes
                ],
                suggested_advance_rate_bps=decision.advance_rate_bps,
                suggested_advance_amount_usdc=decision.advance_amount_usdc,
                model_name=self._agents.model_name,
                policy_version=self._risk_policy.policy_version,
                generated_at=datetime.now(UTC).isoformat(),
            )
            invoice.status = InvoiceStatus.OFFER_READY
            self._append_trace(
                invoice,
                source="RISK_AGENT",
                target="TREASURY_AGENT",
                status="COMPLETED",
                summary=risk_result.risk_passport.summary,
            )
            await self._persist()

    async def respond_to_offer(
        self,
        invoice_id: str,
        response: OfferResponse,
    ) -> tuple[Invoice, bool]:
        """Apply an offer response and report whether funding should be scheduled."""

        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            if response is OfferResponse.ACCEPT and invoice.status is InvoiceStatus.FUNDING:
                should_schedule = (
                    invoice.funding_transaction is None
                    or invoice.funding_transaction.status is TransactionStatus.PENDING
                )
                return self._copy_invoice(invoice), should_schedule
            if response is OfferResponse.ACCEPT and invoice.status is InvoiceStatus.FUNDED:
                return self._copy_invoice(invoice), False
            if response is OfferResponse.DECLINE and invoice.status is InvoiceStatus.BLOCKED:
                return self._copy_invoice(invoice), False
            if invoice.status is not InvoiceStatus.OFFER_READY:
                raise StateConflictError(
                    "OFFER_READY 상태에서만 조기정산 조건에 응답할 수 있습니다."
                )
            if response is OfferResponse.DECLINE:
                invoice.status = InvoiceStatus.BLOCKED
                await self._persist()
                return self._copy_invoice(invoice), False

            invoice.status = InvoiceStatus.FUNDING
            await self._persist()
            return self._copy_invoice(invoice), True

    async def complete_funding(self, invoice_id: str) -> None:
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            if invoice.status is not InvoiceStatus.FUNDING:
                return
            rejection = self._mandate_policy.rejection_reason(invoice)
            if rejection is not None:
                invoice.status = InvoiceStatus.BLOCKED
                self._append_trace(
                    invoice,
                    source="TREASURY_AGENT",
                    target="SETTLEMENT_AGENT",
                    status="FAILED",
                    summary=f"AP2 Mandate 차단: {rejection}",
                )
                await self._persist()
                return

            passport = invoice.risk_passport
            if passport is None or passport.suggested_advance_amount_usdc is None:
                invoice.status = InvoiceStatus.BLOCKED
                await self._persist()
                return
            amount = passport.suggested_advance_amount_usdc
            try:
                result = await self._solana.send_usdc(
                    wallet_id=self._settings.privy_treasury_wallet_id
                    or "MOCK_TREASURY",
                    transfers=[
                        ChainTransfer(
                            to_address=invoice.supplier.wallet_address or "",
                            amount_usdc=amount,
                        )
                    ],
                    reference_id=f"funding-{invoice.id}",
                )
            except IntegrationError as exc:
                invoice.status = InvoiceStatus.ERROR
                self._append_trace(
                    invoice,
                    source="TREASURY_AGENT",
                    target="SETTLEMENT_AGENT",
                    status="FAILED",
                    summary="Solana 조기정산금 전송에 실패했습니다.",
                )
                logger.error("Funding failed for %s: %s", invoice.id, exc)
                await self._persist()
                return

            invoice.funding_transaction = self._transaction(
                result=result,
                amount_usdc=amount,
                to_address=invoice.supplier.wallet_address or "",
            )
            if result.status is TransactionStatus.CONFIRMED:
                invoice.status = InvoiceStatus.FUNDED
                self._append_trace(
                    invoice,
                    source="TREASURY_AGENT",
                    target="SETTLEMENT_AGENT",
                    status="COMPLETED",
                    summary="AP2 Mandate 검증과 Solana Devnet USDC 전송을 완료했습니다.",
                )
            await self._persist()

    async def settle_mock_payment(self, invoice_id: str) -> Invoice:
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            if invoice.status is InvoiceStatus.SETTLED:
                return self._copy_invoice(invoice)
            if invoice.status not in {
                InvoiceStatus.FUNDED,
                InvoiceStatus.REPAYMENT_PENDING,
                InvoiceStatus.SETTLING,
            }:
                raise StateConflictError(
                    "펀딩 완료 후에만 Mock 입금과 정산을 처리할 수 있습니다."
                )

            invoice.status = InvoiceStatus.SETTLING
            try:
                result = await self._solana.send_usdc(
                    wallet_id=self._settings.privy_settlement_wallet_id
                    or "MOCK_SETTLEMENT",
                    transfers=[
                        ChainTransfer(
                            to_address=self._settings.investor_settlement_wallet_address,
                            amount_usdc=19_800,
                        ),
                        ChainTransfer(
                            to_address=self._settings.platform_fee_wallet_address,
                            amount_usdc=200,
                        ),
                    ],
                    reference_id=f"settlement-{invoice.id}",
                )
            except IntegrationError:
                invoice.status = InvoiceStatus.ERROR
                await self._persist()
                raise

            invoice.settlement_transaction = self._transaction(
                result=result,
                amount_usdc=20_000,
                to_address=self._settings.investor_settlement_wallet_address,
            )
            if result.status is TransactionStatus.CONFIRMED:
                invoice.settlement = Settlement(
                    invoice_face_value_usdc=20_000,
                    investor_settlement_usdc=19_800,
                    platform_fee_usdc=200,
                    supplier_residual_usdc=0,
                )
                invoice.status = InvoiceStatus.SETTLED
                self._append_trace(
                    invoice,
                    source="SETTLEMENT_AGENT",
                    target="SETTLEMENT_AGENT",
                    status="COMPLETED",
                    summary=(
                        f"{'SANDBOX ' if result.sandbox else ''}"
                        "KRW 입금 확인과 USDC 정산 분배를 완료했습니다."
                    ),
                )
            await self._persist()
            return self._copy_invoice(invoice)

    def investor_dashboard(self) -> InvestorDashboard:
        active = {
            InvoiceStatus.FUNDED,
            InvoiceStatus.REPAYMENT_PENDING,
            InvoiceStatus.SETTLING,
        }
        outstanding = sum(
            invoice.risk_passport.suggested_advance_amount_usdc or 0
            for invoice in self._invoices.values()
            if invoice.status in active and invoice.risk_passport is not None
        )
        traces = sorted(
            (
                trace
                for invoice in self._invoices.values()
                for trace in invoice.agent_traces
            ),
            key=lambda trace: trace.created_at,
            reverse=True,
        )[:20]
        return InvestorDashboard(
            investor_name="Nova Capital",
            automated_investment_active=True,
            mandate_status="ACTIVE",
            available_vault_usdc=50_000,
            outstanding_principal_usdc=outstanding,
            recent_agent_traces=[trace.model_copy(deep=True) for trace in traces],
        )

    async def close(self) -> None:
        await self._solana.aclose()

    @property
    def settings(self) -> BackendSettings:
        return self._settings

    def _snapshot(self) -> PersistedState:
        return PersistedState(
            invoices=self._invoices,
            verifications=self._verifications,
            agent_analyses=self._agent_analyses,
            invoice_sequence=self._invoice_sequence,
            verification_sequence=self._verification_sequence,
            document_sequence=self._document_sequence,
            trace_sequence=self._trace_sequence,
        )

    async def _persist(self) -> None:
        """Snapshot the aggregate state after a mutation, off the event loop.

        Each snapshot covers every invoice, so building and writing must stay
        serialized: otherwise a slower writer could replace a newer snapshot
        with its own stale one.
        """

        async with self._persist_lock:
            snapshot = self._snapshot()
            await asyncio.to_thread(self._state_store.save, snapshot)

    async def _reserve_invoice_ids(self, document_count: int) -> tuple[str, list[str]]:
        async with self._sequence_lock:
            self._invoice_sequence += 1
            invoice_id = (
                f"INV-{datetime.now(UTC).year}-"
                f"{str(self._invoice_sequence).zfill(3)}"
            )
            document_ids = self._next_document_ids(document_count)
        return invoice_id, document_ids

    async def _reserve_document_ids(self, document_count: int) -> list[str]:
        async with self._sequence_lock:
            return self._next_document_ids(document_count)

    def _next_document_ids(self, document_count: int) -> list[str]:
        document_ids = []
        for _ in range(document_count):
            self._document_sequence += 1
            document_ids.append(f"DOC-{str(self._document_sequence).zfill(3)}")
        return document_ids

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
        ) -> dict[str, object]:
            for document in result.documents:
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
                    (
                        evidence
                        for evidence in document.source_evidence
                        if evidence.field == alias
                    ),
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
            invoice_number=field("invoice_number", "invoiceNumber"),
            supplier_name=field("supplier_name", "supplierName"),
            buyer_name=field("buyer_name", "buyerName"),
            amount_krw=field("total_amount", "totalAmount", self._parse_amount),
            due_date=field("due_date", "dueDate"),
            contract_number=field("contract_number", "contractNumber"),
            purchase_order_number=field(
                "purchase_order_number",
                "purchaseOrderNumber",
            ),
            delivery_completed=field("delivery_completed", "deliveryCompleted"),
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
        invoice.invoice_amount_krw = analysis.amount_krw.value or invoice.invoice_amount_krw
        invoice.due_date = analysis.due_date.value or invoice.due_date
        invoice.contract_number = (
            analysis.contract_number.value or invoice.contract_number
        )
        invoice.purchase_order_number = (
            analysis.purchase_order_number.value or invoice.purchase_order_number
        )
        invoice.supplier.name = analysis.supplier_name.value or invoice.supplier.name
        invoice.buyer.name = analysis.buyer_name.value or invoice.buyer.name
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
            evidence
            for document in analysis.documents
            for evidence in document.source_evidence
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
                code=(
                    "DOCUMENT_MISMATCH"
                    if analysis.mismatches
                    else "DOCUMENT_CONSISTENCY"
                ),
                title=(
                    "문서 불일치 검토 필요"
                    if analysis.mismatches
                    else "핵심 문서 조건 일치"
                ),
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
        amount_usdc: int,
        to_address: str,
    ) -> BlockchainTransaction:
        return BlockchainTransaction(
            signature=result.signature,
            status=result.status,
            amount_usdc=amount_usdc,
            from_address=result.from_address,
            to_address=to_address,
            explorer_url=(
                f"https://explorer.solana.com/tx/{result.signature}?cluster=devnet"
            ),
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

    def _invoice(self, invoice_id: str) -> Invoice:
        try:
            return self._invoices[invoice_id]
        except KeyError as exc:
            raise NotFoundError(f"Invoice {invoice_id}를 찾을 수 없습니다.") from exc

    def _verification(self, verification_id: str) -> Verification:
        try:
            return self._verifications[verification_id]
        except KeyError as exc:
            raise NotFoundError(
                f"Verification {verification_id}를 찾을 수 없습니다."
            ) from exc

    def _invoice_lock(self, invoice_id: str) -> asyncio.Lock:
        return self._invoice_locks.setdefault(invoice_id, asyncio.Lock())

    @staticmethod
    def _copy_invoice(invoice: Invoice) -> Invoice:
        return invoice.model_copy(deep=True)

    @staticmethod
    def _parse_amount(value: object) -> int:
        digits = re.sub(r"[^\d]", "", str(value))
        if not digits:
            raise ValueError("amount does not contain digits")
        return int(digits)

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
