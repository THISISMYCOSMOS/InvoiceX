"""Adapters that call the existing InvoiceX Document and Risk Agent package."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from invoicex_agents import (
    AgentSettings,
    DocumentAgent,
    GoogleGeminiClient,
    RiskAgent,
    StaticGeminiClient,
)
from invoicex_agents.clients.base import MediaDocument
from invoicex_agents.models.document import DocumentAnalysisResult
from invoicex_agents.models.risk import RiskAnalysisRequest, RiskAnalysisResult

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import DocumentType


@dataclass(frozen=True, slots=True)
class AgentDocument:
    """Document bytes plus the frontend document classification."""

    document_id: str
    type: DocumentType
    mime_type: str
    data: bytes

    def to_media(self) -> MediaDocument:
        return MediaDocument(
            document_id=self.document_id,
            mime_type=self.mime_type,
            data=self.data,
        )


class AgentGateway(Protocol):
    """Backend-facing interface implemented by real and deterministic agents."""

    mode: str
    model_name: str

    async def analyze_documents(
        self,
        invoice_id: str,
        documents: list[AgentDocument],
    ) -> DocumentAnalysisResult:
        """Run the existing Document Agent."""

    async def analyze_risk(self, request: RiskAnalysisRequest) -> RiskAnalysisResult:
        """Run the existing Risk Agent."""


class RealAgentGateway:
    """Gemini-backed adapter preserving the existing Agent package boundaries."""

    mode = "real"

    def __init__(self, settings: BackendSettings) -> None:
        agent_settings = AgentSettings(
            GEMINI_API_KEY=settings.gemini_api_key,
            GEMINI_MODEL=settings.gemini_model,
        )
        client = GoogleGeminiClient(agent_settings)
        self._document_agent = DocumentAgent(client)
        self._risk_agent = RiskAgent(client)
        self._semaphore = asyncio.Semaphore(4)
        self.model_name = settings.gemini_model

    async def analyze_documents(
        self,
        invoice_id: str,
        documents: list[AgentDocument],
    ) -> DocumentAnalysisResult:
        del invoice_id
        async with self._semaphore:
            return await asyncio.to_thread(
                self._document_agent.analyze,
                [document.to_media() for document in documents],
            )

    async def analyze_risk(self, request: RiskAnalysisRequest) -> RiskAnalysisResult:
        async with self._semaphore:
            return await asyncio.to_thread(self._risk_agent.analyze, request)


class MockAgentGateway:
    """Deterministic Agent adapter for local development and stress tests."""

    mode = "mock"
    model_name = "static-gemini-client"

    async def analyze_documents(
        self,
        invoice_id: str,
        documents: list[AgentDocument],
    ) -> DocumentAnalysisResult:
        response = self._document_response(invoice_id, documents)
        # Mock mode is used for deterministic workflow tests. Upload validation
        # remains the backend's responsibility, while real document parsing and
        # source-evidence checks are covered by the Document Agent in real mode.
        return DocumentAnalysisResult.model_validate(response)

    async def analyze_risk(self, request: RiskAnalysisRequest) -> RiskAnalysisResult:
        narrative = {
            "riskReasons": [
                {
                    "factorCode": factor.code,
                    "explanation": self._factor_explanation(factor.code),
                    "sourceEvidenceIds": factor.source_evidence_ids,
                }
                for factor in request.risk_factors
            ],
            "reviewRequired": request.risk_level != "POLICY_ACCEPTABLE",
            "riskPassportSummary": (
                "Buyer 확인과 제출 문서의 핵심 거래 조건을 바탕으로 "
                "결정론적 투자 정책을 검증했습니다."
            ),
        }
        agent = RiskAgent(StaticGeminiClient(narrative))
        return await asyncio.to_thread(agent.analyze, request)

    @classmethod
    def _document_response(
        cls,
        invoice_id: str,
        documents: list[AgentDocument],
    ) -> dict[str, object]:
        now = datetime.now(UTC)
        year = now.year
        issue_date = now.date().isoformat()
        due_date = (now + timedelta(days=90)).date().isoformat()
        shared = {
            "supplierName": "Alpha Components",
            "buyerName": "Prime Mobility",
            "currency": "KRW",
            "totalAmount": "3000",
        }
        values_by_type: dict[DocumentType, dict[str, object]] = {
            DocumentType.INVOICE: {
                **shared,
                "invoiceNumber": invoice_id,
                "issueDate": issue_date,
                "dueDate": due_date,
            },
            DocumentType.CONTRACT: {
                **shared,
                "contractNumber": f"PM-SUPPLY-{year}-04",
                "paymentTerms": "Invoice due date settlement",
            },
            DocumentType.PURCHASE_ORDER: {
                **shared,
                "purchaseOrderNumber": f"PO-{89340 + int(invoice_id[-3:])}",
                "itemName": "Demo components",
                "quantity": "100",
                "unitPrice": "30",
            },
            DocumentType.DELIVERY_PROOF: {
                "supplierName": "Alpha Components",
                "buyerName": "Prime Mobility",
                "itemName": "Demo components",
                "quantity": "100",
                "deliveryCompleted": True,
            },
        }
        agent_type = {
            DocumentType.INVOICE: "INVOICE",
            DocumentType.CONTRACT: "CONTRACT",
            DocumentType.PURCHASE_ORDER: "PURCHASE_ORDER",
            DocumentType.DELIVERY_PROOF: "DELIVERY_EVIDENCE",
        }
        all_fields = [
            "invoiceNumber",
            "supplierName",
            "buyerName",
            "purchaseOrderNumber",
            "contractNumber",
            "currency",
            "totalAmount",
            "issueDate",
            "dueDate",
            "itemName",
            "quantity",
            "unitPrice",
            "paymentTerms",
            "deliveryCompleted",
        ]
        analyzed_documents: list[dict[str, object]] = []
        for document in documents:
            populated = values_by_type[document.type]
            extracted = {field: populated.get(field) for field in all_fields}
            evidence = [
                {
                    "evidenceId": f"{document.document_id}-{field}",
                    "documentId": document.document_id,
                    "page": 1,
                    "field": field,
                    "quote": str(value),
                }
                for field, value in populated.items()
            ]
            analyzed_documents.append(
                {
                    "documentId": document.document_id,
                    "documentType": agent_type[document.type],
                    "extractedData": extracted,
                    "missingFields": [
                        field for field in all_fields if extracted[field] is None
                    ],
                    "sourceEvidence": evidence,
                }
            )
        return {
            "schemaVersion": "document-agent.v1",
            "documents": analyzed_documents,
            "mismatches": [],
            "reviewRequired": True,
        }

    @staticmethod
    def _factor_explanation(code: str) -> str:
        explanations = {
            "BUYER_CONFIRMED": "구매기업이 거래 사실과 지급 의무를 확인했습니다.",
            "DOCUMENT_CONSISTENCY": "제출 문서의 핵심 금액과 거래 당사자가 일치합니다.",
            "DOCUMENT_MISMATCH": "제출 문서 사이의 불일치로 추가 검토가 필요합니다.",
            "LIMITED_HISTORY": "현재 평가는 단일 Demo 거래 이력을 기준으로 합니다.",
        }
        return explanations.get(code, "백엔드가 제공한 검증 사실을 확인했습니다.")


def create_agent_gateway(settings: BackendSettings) -> AgentGateway:
    """Select real Gemini or deterministic mock once at application startup."""

    if settings.resolved_agent_mode() == "real":
        return RealAgentGateway(settings)
    return MockAgentGateway()
