"""Reusable deterministic fixtures for agent tests."""

from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def valid_document_response() -> dict[str, Any]:
    return {
        "schemaVersion": "document-agent.v1",
        "documents": [
            {
                "documentId": "invoice-1",
                "documentType": "INVOICE",
                "extractedData": {
                    "invoiceNumber": "INV-2026-001",
                    "supplierName": "Alpha Components",
                    "buyerName": "Prime Mobility",
                    "purchaseOrderNumber": None,
                    "contractNumber": None,
                    "currency": "KRW",
                    "totalAmount": "20000000",
                    "issueDate": "2026-07-29",
                    "dueDate": "2026-10-30",
                    "itemName": None,
                    "quantity": None,
                    "unitPrice": None,
                    "paymentTerms": None,
                    "deliveryCompleted": None,
                },
                "missingFields": [
                    "purchaseOrderNumber",
                    "contractNumber",
                    "itemName",
                    "quantity",
                    "unitPrice",
                    "paymentTerms",
                    "deliveryCompleted",
                ],
                "sourceEvidence": [
                    {
                        "evidenceId": "ev-invoice-number",
                        "documentId": "invoice-1",
                        "page": 1,
                        "field": "invoiceNumber",
                        "quote": "Invoice No. INV-2026-001",
                    },
                    {
                        "evidenceId": "ev-supplier",
                        "documentId": "invoice-1",
                        "page": 1,
                        "field": "supplierName",
                        "quote": "Alpha Components",
                    },
                    {
                        "evidenceId": "ev-buyer",
                        "documentId": "invoice-1",
                        "page": 1,
                        "field": "buyerName",
                        "quote": "Bill To: Prime Mobility",
                    },
                    {
                        "evidenceId": "ev-currency",
                        "documentId": "invoice-1",
                        "page": 1,
                        "field": "currency",
                        "quote": "KRW",
                    },
                    {
                        "evidenceId": "ev-total",
                        "documentId": "invoice-1",
                        "page": 1,
                        "field": "totalAmount",
                        "quote": "Total 20,000,000",
                    },
                    {
                        "evidenceId": "ev-issue-date",
                        "documentId": "invoice-1",
                        "page": 1,
                        "field": "issueDate",
                        "quote": "2026.07.29",
                    },
                    {
                        "evidenceId": "ev-due-date",
                        "documentId": "invoice-1",
                        "page": 1,
                        "field": "dueDate",
                        "quote": "Due 2026.10.30",
                    },
                ],
            }
        ],
        "mismatches": [],
        "reviewRequired": False,
    }


@pytest.fixture
def valid_risk_request_data() -> dict[str, Any]:
    return {
        "invoiceId": "INV-2026-001",
        "buyerDecision": "CONFIRM",
        "riskScore": 86,
        "riskLevel": "POLICY_ACCEPTABLE",
        "riskFactors": [
            {
                "code": "DOCUMENT_MATCH",
                "title": "문서 일치",
                "facts": ["인보이스 금액과 Buyer 확인 금액이 일치함"],
                "sourceEvidenceIds": ["ev-total"],
            }
        ],
        "sourceEvidence": [
            {
                "evidenceId": "ev-total",
                "documentId": "invoice-1",
                "page": 1,
                "field": "totalAmount",
                "quote": "Total 20,000,000",
            }
        ],
    }


@pytest.fixture
def valid_risk_narrative() -> dict[str, Any]:
    return {
        "riskReasons": [
            {
                "factorCode": "DOCUMENT_MATCH",
                "explanation": "확인된 금액이 제출 문서의 금액과 일치합니다.",
                "sourceEvidenceIds": ["ev-total"],
            }
        ],
        "reviewRequired": False,
        "riskPassportSummary": "Buyer 확인과 문서 금액 일치가 확인되었습니다.",
    }


@pytest.fixture
def copy_dict() -> Callable[[dict[str, Any]], dict[str, Any]]:
    import copy

    return copy.deepcopy
