"""Run a deterministic concurrent stress test for the Document and Risk agents."""

from __future__ import annotations

import argparse
import json
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

from invoicex_agents.agents.document import DocumentAgent
from invoicex_agents.agents.risk import RiskAgent
from invoicex_agents.clients.base import MediaDocument
from invoicex_agents.clients.mock import StaticGeminiClient
from invoicex_agents.models.risk import RiskAnalysisRequest

EMPTY_DOCUMENT_FIELDS = [
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


def _document_response(document_id: str) -> dict[str, object]:
    return {
        "schemaVersion": "document-agent.v1",
        "documents": [
            {
                "documentId": document_id,
                "documentType": "INVOICE",
                "extractedData": {field: None for field in EMPTY_DOCUMENT_FIELDS},
                "missingFields": EMPTY_DOCUMENT_FIELDS,
                "sourceEvidence": [],
            }
        ],
        "mismatches": [],
        "reviewRequired": False,
    }


def _risk_request(invoice_id: str, evidence_id: str) -> RiskAnalysisRequest:
    return RiskAnalysisRequest.model_validate(
        {
            "invoiceId": invoice_id,
            "buyerDecision": "CONFIRM",
            "riskScore": 86,
            "riskLevel": "POLICY_ACCEPTABLE",
            "riskFactors": [
                {
                    "code": "DOCUMENT_MATCH",
                    "title": "문서 일치",
                    "facts": ["확정 금액과 문서 금액이 일치함"],
                    "sourceEvidenceIds": [evidence_id],
                }
            ],
            "sourceEvidence": [
                {
                    "evidenceId": evidence_id,
                    "documentId": invoice_id,
                    "page": 1,
                    "field": "totalAmount",
                    "quote": "Total 20,000,000",
                }
            ],
        }
    )


def _risk_narrative(evidence_id: str) -> dict[str, object]:
    return {
        "riskReasons": [
            {
                "factorCode": "DOCUMENT_MATCH",
                "explanation": "확정 금액과 문서 금액이 일치합니다.",
                "sourceEvidenceIds": [evidence_id],
            }
        ],
        "reviewRequired": False,
        "riskPassportSummary": "문서 금액 일치가 확인되었습니다.",
    }


def _run_iteration(index: int) -> int:
    document_id = f"invoice-{index}"
    document_client = StaticGeminiClient(_document_response(document_id))
    document_result = DocumentAgent(document_client).analyze(
        [MediaDocument(document_id, "application/pdf", b"%PDF-synthetic")]
    )
    if document_result.documents[0].document_id != document_id:
        raise AssertionError("Document Agent changed the supplied document ID")
    if len(document_client.calls) != 1:
        raise AssertionError("Document Agent made an unexpected number of client calls")

    evidence_id = f"evidence-{index}"
    risk_client = StaticGeminiClient(_risk_narrative(evidence_id))
    risk_result = RiskAgent(risk_client).analyze(_risk_request(document_id, evidence_id))
    if risk_result.risk_score != 86 or risk_result.risk_level != "POLICY_ACCEPTABLE":
        raise AssertionError("Risk Agent changed a deterministic backend decision")
    if risk_result.risk_passport.source_evidence_ids != [evidence_id]:
        raise AssertionError("Risk Agent lost or changed source evidence")
    if len(risk_client.calls) != 1:
        raise AssertionError("Risk Agent made an unexpected number of client calls")
    return 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    tracemalloc.start()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        completed_operations = sum(executor.map(_run_iteration, range(args.iterations)))
    elapsed_seconds = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(
        json.dumps(
            {
                "iterations": args.iterations,
                "workers": args.workers,
                "agentOperations": completed_operations,
                "elapsedSeconds": round(elapsed_seconds, 3),
                "operationsPerSecond": round(completed_operations / elapsed_seconds, 1),
                "peakTracedMemoryMiB": round(peak_bytes / 1024 / 1024, 2),
                "failures": 0,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
