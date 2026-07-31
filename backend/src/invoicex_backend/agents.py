"""Adapters that call the existing InvoiceX Document and Risk Agent package."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
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

SEED_DOCUMENT_FIELDS = (
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
)

_SUPPLIER = ("(주)알파컴포넌츠", "공급기업: (주)알파컴포넌츠")
_BUYER = ("(주)프라임모빌리티", "구매기업: (주)프라임모빌리티")
_CURRENCY = ("KRW", "통화: KRW")
_ITEM = ("정밀 가공 부품", "품목: 정밀 가공 부품")
_QUANTITY = ("100", "수량: 100")
_UNIT_PRICE = ("200000", "단가: 200,000 KRW")
_PAYMENT_TERMS = (
    "청구서 발행일로부터 93일 이내 지급",
    "지급 조건: 청구서 발행일로부터 93일 이내 지급",
)

# Values and quotes taken verbatim from backend/seed so the deterministic mock
# survives the Document Agent's source-evidence validation: every quote must be
# findable on the PDF page and must support the extracted value.
SEED_DOCUMENT_FACTS: dict[DocumentType, dict[str, tuple[object, str]]] = {
    DocumentType.INVOICE: {
        "invoiceNumber": ("INV-2026-0001", "인보이스 번호: INV-2026-0001"),
        "supplierName": _SUPPLIER,
        "buyerName": _BUYER,
        "contractNumber": ("CT-2026-0007", "계약번호: CT-2026-0007"),
        "purchaseOrderNumber": ("PO-2026-1001", "발주번호: PO-2026-1001"),
        "currency": _CURRENCY,
        "totalAmount": ("20000000", "공급가액 합계: 20,000,000 KRW"),
        "issueDate": ("2026-07-29", "발행일: 2026-07-29"),
        "dueDate": ("2026-10-30", "지급 만기일: 2026-10-30"),
        "itemName": _ITEM,
        "quantity": _QUANTITY,
        "unitPrice": _UNIT_PRICE,
        "paymentTerms": _PAYMENT_TERMS,
        "deliveryCompleted": (True, "납품 완료 여부: 완료"),
    },
    DocumentType.CONTRACT: {
        "supplierName": _SUPPLIER,
        "buyerName": _BUYER,
        "contractNumber": ("CT-2026-0007", "계약번호: CT-2026-0007"),
        "currency": _CURRENCY,
        "itemName": ("정밀 가공 부품", "계약 품목: 정밀 가공 부품"),
        "unitPrice": ("200000", "계약 단가: 200,000 KRW"),
        "paymentTerms": (
            "청구서 발행일로부터 93일 이내 지급",
            "대금 지급 조건: 청구서 발행일로부터 93일 이내 지급",
        ),
    },
    DocumentType.PURCHASE_ORDER: {
        "supplierName": _SUPPLIER,
        "buyerName": _BUYER,
        "contractNumber": ("CT-2026-0007", "계약번호: CT-2026-0007"),
        "purchaseOrderNumber": ("PO-2026-1001", "발주번호: PO-2026-1001"),
        "currency": _CURRENCY,
        "totalAmount": ("20000000", "발주 금액: 20,000,000 KRW"),
        "issueDate": ("2026-07-01", "발주일: 2026-07-01"),
        "itemName": _ITEM,
        "quantity": _QUANTITY,
        "unitPrice": _UNIT_PRICE,
    },
    DocumentType.DELIVERY_PROOF: {
        "supplierName": _SUPPLIER,
        "buyerName": _BUYER,
        "purchaseOrderNumber": ("PO-2026-1001", "발주번호: PO-2026-1001"),
        "currency": _CURRENCY,
        "totalAmount": ("20000000", "공급가액 합계: 20,000,000 KRW"),
        "issueDate": ("2026-07-24", "발행일: 2026-07-24"),
        "itemName": _ITEM,
        "quantity": _QUANTITY,
        "unitPrice": _UNIT_PRICE,
        "deliveryCompleted": (True, "인수 확인: 발주 수량 전량 납품 완료"),
    },
}


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
        agent = DocumentAgent(StaticGeminiClient(response))
        return await asyncio.to_thread(
            agent.analyze,
            [document.to_media() for document in documents],
        )

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
        del invoice_id
        agent_type = {
            DocumentType.INVOICE: "INVOICE",
            DocumentType.CONTRACT: "CONTRACT",
            DocumentType.PURCHASE_ORDER: "PURCHASE_ORDER",
            DocumentType.DELIVERY_PROOF: "DELIVERY_EVIDENCE",
        }
        analyzed_documents: list[dict[str, object]] = []
        for document in documents:
            populated = SEED_DOCUMENT_FACTS[document.type]
            extracted = {
                field: populated[field][0] if field in populated else None
                for field in SEED_DOCUMENT_FIELDS
            }
            evidence = [
                {
                    "evidenceId": f"{document.document_id}-{field}",
                    "documentId": document.document_id,
                    "page": 1,
                    "field": field,
                    "quote": quote,
                }
                for field, (_, quote) in populated.items()
            ]
            analyzed_documents.append(
                {
                    "documentId": document.document_id,
                    "documentType": agent_type[document.type],
                    "extractedData": extracted,
                    "missingFields": [
                        field
                        for field in SEED_DOCUMENT_FIELDS
                        if extracted[field] is None
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
