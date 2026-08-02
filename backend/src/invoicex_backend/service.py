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
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from invoicex_agents.exceptions import AgentError
from invoicex_agents.models.common import SourceEvidence
from invoicex_agents.models.document import DocumentAnalysisResult
from invoicex_agents.models.risk import RiskAnalysisRequest, RiskFactorContext
from solders.pubkey import Pubkey
from solders.signature import Signature

from invoicex_backend.agents import AgentDocument, AgentGateway
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import (
    DocumentValidationError,
    IntegrationError,
    NotFoundError,
    StateConflictError,
)
from invoicex_backend.models import (
    AgentDecision,
    AgentTrace,
    AnalysisStatus,
    BlockchainTransaction,
    ChainTransfer,
    ChainTransferResult,
    ConfirmVaultDepositRequest,
    CreateMandateRequest,
    DocumentAnalysis,
    DocumentType,
    ExtractedFieldStatus,
    InvestorDashboard,
    InvestorMandate,
    Invoice,
    InvoiceParty,
    InvoiceStatus,
    MandatePolicy,
    OfferResponse,
    PositiveFactor,
    RiskFactor,
    RiskPassport,
    RwaAsset,
    Settlement,
    SponsorVaultDepositRequest,
    TransactionStatus,
    UploadedDocument,
    VaultBalance,
    Verification,
    VerificationStatus,
)
from invoicex_backend.policy import (
    DeterministicRiskPolicy,
    RiskDecision,
)
from invoicex_backend.repository import RwaRepository, SQLiteRwaRepository
from invoicex_backend.solana import SolanaGateway
from invoicex_backend.storage import DocumentStorage

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
    amount_usdc: int
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
    ) -> None:
        self._settings = settings
        self._agents = agent_gateway
        self._solana = solana_gateway
        self._storage = storage
        self._repository = repository or SQLiteRwaRepository(settings.rwa_database_path)
        self._risk_policy = DeterministicRiskPolicy()
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

    async def create_invoice(self, uploads: list[UploadedDocument]) -> Invoice:
        self._validate_uploads(uploads)
        invoice_id, document_ids = await self._reserve_invoice_ids(len(uploads))
        now = datetime.now(UTC)
        invoice_number = int(invoice_id[-3:])
        invoice = Invoice(
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
            invoice_amount_krw=3_000,
            issue_date=now.date().isoformat(),
            due_date=(now + timedelta(days=90)).date().isoformat(),
            delivery_date=(now - timedelta(days=5)).date().isoformat(),
            contract_number=f"PM-SUPPLY-{now.year}-04",
            purchase_order_number=f"PO-{89340 + invoice_number}",
            status=InvoiceStatus.DOCUMENT_ANALYZING,
            verification_id=None,
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
            agent_documents = [
                AgentDocument(
                    document_id=document_id,
                    type=upload.type,
                    mime_type=upload.mime_type,
                    data=upload.data,
                )
                for document_id, upload in zip(document_ids, uploads, strict=True)
            ]
            agent_result = await self._agents.analyze_documents(
                invoice_id,
                agent_documents,
            )
        except AgentError as exc:
            invoice.status = InvoiceStatus.ERROR
            raise IntegrationError(f"Gemini 문서 분석에 실패했습니다: {exc}") from exc
        except OSError as exc:
            invoice.status = InvoiceStatus.ERROR
            raise IntegrationError("업로드 문서를 저장하지 못했습니다.") from exc

        self._agent_analyses[invoice_id] = agent_result
        self._repository.save_analysis(invoice_id, agent_result)
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
        self._save_invoice(invoice)
        return self._copy_invoice(invoice)

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

    def save_supplier_wallet(self, wallet_address: str) -> None:
        self._validate_wallet_address(wallet_address)
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
        if self._repository.get_vault(mandate.owner_wallet_address) is None:
            self._repository.save_vault(
                VaultBalance(
                    owner_wallet_address=mandate.owner_wallet_address,
                    vault_address=mandate.vault_address,
                    available_usdc=0,
                    updated_at=now,
                )
            )
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
        self._validate_wallet_address(owner_wallet_address)
        existing = self._repository.get_vault(owner_wallet_address)
        if existing is not None:
            return existing
        return VaultBalance(
            owner_wallet_address=owner_wallet_address,
            vault_address=self._solana.vault_address,
            available_usdc=0,
            updated_at=datetime.now(UTC).isoformat(),
        )

    async def prepare_vault_deposit(self, *, owner_wallet_address: str, amount_usdc: int):
        self._validate_wallet_address(owner_wallet_address)
        prepared = await self._solana.prepare_vault_deposit(
            owner_wallet_address=owner_wallet_address, amount_usdc=amount_usdc
        )
        if not prepared.sponsored:
            return prepared
        if amount_usdc > self._settings.gasless_deposit_max_usdc:
            raise StateConflictError(
                "가스리스 예치는 최대 "
                f"{self._settings.gasless_deposit_max_usdc} USDC까지 가능합니다."
            )
        sponsor_deposit_id = secrets.token_urlsafe(24)
        async with self._sponsored_deposit_lock:
            self._sponsored_deposit_intents[sponsor_deposit_id] = PendingSponsoredDeposit(
                owner_wallet_address=owner_wallet_address,
                amount_usdc=amount_usdc,
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
            amount_usdc=intent.amount_usdc,
            prepared_transaction_base64=intent.prepared_transaction_base64,
            signed_transaction_base64=request.signed_transaction_base64,
            reference_id=f"gasless-deposit-{request.sponsor_deposit_id[:20]}",
        )
        return await self.confirm_vault_deposit(
            ConfirmVaultDepositRequest(
                owner_wallet_address=intent.owner_wallet_address,
                amount_usdc=intent.amount_usdc,
                signature=result.signature,
            )
        )

    async def confirm_vault_deposit(self, request: ConfirmVaultDepositRequest) -> VaultBalance:
        self._validate_wallet_address(request.owner_wallet_address)
        if not await self._solana.verify_vault_deposit(
            signature=request.signature,
            owner_wallet_address=request.owner_wallet_address,
            amount_usdc=request.amount_usdc,
        ):
            raise StateConflictError("Agent Vault 예치 트랜잭션을 확인하지 못했습니다.")
        if not self._repository.claim_deposit(request.signature):
            return self.get_vault(request.owner_wallet_address)
        current = self.get_vault(request.owner_wallet_address)
        updated = current.model_copy(
            update={
                "available_usdc": current.available_usdc + request.amount_usdc,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        self._repository.save_vault(updated)
        return updated

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
                    f"VER-{datetime.now(UTC).year}-{str(self._verification_sequence).zfill(3)}"
                )
            verification = Verification(
                id=verification_id,
                invoice_id=invoice_id,
                status=VerificationStatus.PENDING,
            )
            self._verifications[verification_id] = verification
            invoice.verification_id = verification_id
            invoice.status = InvoiceStatus.BUYER_REVIEW
            self._repository.save_verification(verification)
            self._save_invoice(invoice)
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
            agent_analysis = self._agent_analyses[invoice.id]
            decision = self._risk_policy.evaluate(
                has_mismatches=bool(agent_analysis.mismatches),
                face_value_usdc=invoice.invoice_amount_krw // self._settings.demo_krw_per_usdc,
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
            self._repository.save_verification(verification)
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    async def respond_to_offer(
        self,
        invoice_id: str,
        response: OfferResponse,
    ) -> tuple[Invoice, bool]:
        """Issue one RWA unit and then queue automatic mandate evaluation."""

        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
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
                self._repository.get_supplier_wallet() or invoice.supplier.wallet_address
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
                    amount_usdc=0,
                    to_address=issued.escrow_token_account,
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
            quoted_amount = decision.amount_usdc
            amount = (
                min(quoted_amount, self._settings.solana_demo_transfer_amount_usdc)
                if self._solana.mode != "mock"
                else quoted_amount
            )
            if amount != quoted_amount:
                decision = decision.model_copy(
                    update={
                        "amount_usdc": amount,
                        "checks": {
                            **decision.checks,
                            "demoTransferCapApplied": True,
                            "quotedAmountUsdc": quoted_amount,
                            "onchainAmountUsdc": amount,
                        },
                    }
                )
                self._repository.save_decision(decision)
                invoice.agent_decision = decision
            try:
                result = await self._solana.purchase_rwa(
                    invoice_id=invoice.id,
                    rwa_mint_address=asset.mint_address,
                    escrow_token_account=asset.escrow_token_account,
                    supplier_wallet_address=invoice.supplier.wallet_address or "",
                    amount_usdc=amount,
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
                result=result, amount_usdc=amount, to_address=invoice.supplier.wallet_address or ""
            )
            if result.status is TransactionStatus.CONFIRMED:
                sold_asset = asset.model_copy(
                    update={
                        "status": "SOLD",
                        "purchase_transaction": invoice.funding_transaction,
                        "owner_vault_address": vault.vault_address,
                    }
                )
                completed = decision.model_copy(update={"status": "EXECUTED"})
                self._repository.save_rwa_asset(sold_asset)
                self._repository.save_decision(completed)
                self._repository.save_vault(
                    vault.model_copy(
                        update={
                            "available_usdc": vault.available_usdc - amount,
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

    async def settle_mock_payment(self, invoice_id: str) -> Invoice:
        if not self._settings.mock_settlement_enabled:
            raise StateConflictError(
                "Mock 상환 정산은 현재 GCP 자동매수 범위에서 비활성화되어 있습니다."
            )
        async with self._invoice_lock(invoice_id):
            invoice = self._invoice(invoice_id)
            if invoice.status is InvoiceStatus.SETTLED:
                return self._copy_invoice(invoice)
            if invoice.status not in {
                InvoiceStatus.FUNDED,
                InvoiceStatus.REPAYMENT_PENDING,
                InvoiceStatus.SETTLING,
            }:
                raise StateConflictError("펀딩 완료 후에만 Mock 입금과 정산을 처리할 수 있습니다.")

            invoice.status = InvoiceStatus.SETTLING
            try:
                result = await self._solana.send_usdc(
                    wallet_id=self._settings.privy_settlement_wallet_id or "MOCK_SETTLEMENT",
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
            self._save_invoice(invoice)
            return self._copy_invoice(invoice)

    def investor_dashboard(self) -> InvestorDashboard:
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
            investor_name="Nova Capital",
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
        invoice.contract_number = analysis.contract_number.value or invoice.contract_number
        invoice.purchase_order_number = (
            analysis.purchase_order_number.value or invoice.purchase_order_number
        )
        invoice.supplier.name = analysis.supplier_name.value or invoice.supplier.name
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
        amount_usdc: int,
        to_address: str,
    ) -> BlockchainTransaction:
        return BlockchainTransaction(
            signature=result.signature,
            status=result.status,
            amount_usdc=amount_usdc,
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
            amount is not None
            and self._repository.committed_for_mandate(mandate.id) + amount
            <= policy.total_investment_limit_usdc
        )
        checks = {
            "policyActive": is_policy_active,
            "riskEligible": bool(passport and passport.eligibility.value == "ELIGIBLE"),
            "minimumRiskScore": is_minimum_risk_score,
            "buyerAllowlist": invoice.buyer.name in policy.buyer_allowlist,
            "maximumRemainingTerm": remaining_days <= policy.maximum_remaining_term_days,
            "perInvoiceLimit": bool(amount is not None and amount <= policy.per_invoice_limit_usdc),
            "totalInvestmentLimit": is_total_investment_within_limit,
            "vaultAvailableBalance": bool(amount is not None and vault.available_usdc >= amount),
        }
        rejected = [name for name, passed in checks.items() if not passed]
        return AgentDecision(
            invoice_id=invoice.id,
            mandate_id=mandate.id,
            status="APPROVED" if not rejected else "REJECTED",
            checks=checks,
            amount_usdc=amount or 0,
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
