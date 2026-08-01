"""Document Agent schema invariant tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from invoicex_agents.models.document import (
    DocumentAnalysisResult,
    DocumentExtractedData,
)


def test_valid_document_result_is_accepted(
    valid_document_response: dict[str, Any],
) -> None:
    result = DocumentAnalysisResult.model_validate(valid_document_response)

    assert result.documents[0].extracted_data.invoice_number == "INV-2026-001"
    assert result.review_required is False


def test_identifier_separator_whitespace_is_canonicalized() -> None:
    extracted = DocumentExtractedData(
        invoiceNumber="INV - 2026 – 001",
        purchaseOrderNumber="PO / 2026 / 1001",
        contractNumber="CT- 2026 -0007",
    )

    assert extracted.invoice_number == "INV-2026-001"
    assert extracted.purchase_order_number == "PO/2026/1001"
    assert extracted.contract_number == "CT-2026-0007"


def test_non_null_extracted_value_without_evidence_is_rejected(
    valid_document_response: dict[str, Any],
    copy_dict: Any,
) -> None:
    response = copy_dict(valid_document_response)
    response["documents"][0]["sourceEvidence"] = [
        evidence
        for evidence in response["documents"][0]["sourceEvidence"]
        if evidence["field"] != "totalAmount"
    ]

    with pytest.raises(ValidationError, match="require sourceEvidence"):
        DocumentAnalysisResult.model_validate(response)


def test_mismatch_without_complete_evidence_is_rejected(
    valid_document_response: dict[str, Any],
    copy_dict: Any,
) -> None:
    response = copy_dict(valid_document_response)
    second = copy_dict(response["documents"][0])
    second["documentId"] = "purchase-order-1"
    second["documentType"] = "PURCHASE_ORDER"
    for evidence in second["sourceEvidence"]:
        evidence["documentId"] = "purchase-order-1"
        evidence["evidenceId"] = f"po-{evidence['evidenceId']}"
    response["documents"].append(second)
    response["mismatches"] = [
        {
            "field": "totalAmount",
            "values": [
                {"documentId": "invoice-1", "value": "20000000"},
                {"documentId": "purchase-order-1", "value": "19000000"},
            ],
            "description": "금액 불일치",
            "sourceEvidenceIds": ["ev-total", "po-ev-due-date"],
        }
    ]
    response["reviewRequired"] = True

    with pytest.raises(ValidationError, match="field must match"):
        DocumentAnalysisResult.model_validate(response)


def test_undeclared_null_field_is_rejected(
    valid_document_response: dict[str, Any],
    copy_dict: Any,
) -> None:
    response = copy_dict(valid_document_response)
    response["documents"][0]["missingFields"] = []

    with pytest.raises(ValidationError, match="must be listed in missingFields"):
        DocumentAnalysisResult.model_validate(response)


def test_empty_extraction_cannot_claim_completeness(
    valid_document_response: dict[str, Any],
    copy_dict: Any,
) -> None:
    response = copy_dict(valid_document_response)
    document = response["documents"][0]
    document["extractedData"] = dict.fromkeys(document["extractedData"])
    document["missingFields"] = []
    document["sourceEvidence"] = []

    with pytest.raises(ValidationError, match="must be listed in missingFields"):
        DocumentAnalysisResult.model_validate(response)


def test_mismatch_requires_review(
    valid_document_response: dict[str, Any],
    copy_dict: Any,
) -> None:
    response = copy_dict(valid_document_response)
    second = copy_dict(response["documents"][0])
    second["documentId"] = "purchase-order-1"
    second["documentType"] = "PURCHASE_ORDER"
    second["extractedData"]["totalAmount"] = "19000000"
    for evidence in second["sourceEvidence"]:
        evidence["documentId"] = "purchase-order-1"
        evidence["evidenceId"] = f"po-{evidence['evidenceId']}"
    response["documents"].append(second)
    response["mismatches"] = [
        {
            "field": "totalAmount",
            "values": [
                {"documentId": "invoice-1", "value": "20000000"},
                {"documentId": "purchase-order-1", "value": "19000000"},
            ],
            "description": "금액 불일치",
            "sourceEvidenceIds": ["ev-total", "po-ev-total"],
        }
    ]
    response["reviewRequired"] = False

    with pytest.raises(ValidationError, match="reviewRequired"):
        DocumentAnalysisResult.model_validate(response)


def test_missing_field_alone_does_not_force_review(
    valid_document_response: dict[str, Any],
) -> None:
    result = DocumentAnalysisResult.model_validate(valid_document_response)

    assert result.documents[0].missing_fields
    assert result.review_required is False


def test_numeric_date_and_currency_fields_are_canonicalized() -> None:
    extracted = DocumentExtractedData.model_validate(
        {
            "currency": "krw",
            "totalAmount": "KRW 20,000,000",
            "quantity": "1,000 EA",
            "unitPrice": "20,000 KRW",
            "issueDate": "2026. 07. 29",
            "dueDate": "2026년 10월 30일",
        }
    )

    assert extracted.currency == "KRW"
    assert extracted.total_amount == "20000000"
    assert extracted.quantity == "1000"
    assert extracted.unit_price == "20000"
    assert extracted.issue_date == "2026-07-29"
    assert extracted.due_date == "2026-10-30"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("currency", "BANANA"),
        ("totalAmount", "approximately lots"),
        ("quantity", "zero-ish"),
        ("unitPrice", "-100"),
        ("issueDate", "tomorrow"),
        ("dueDate", "2026-02-30"),
    ],
)
def test_malformed_document_values_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        DocumentExtractedData.model_validate({field: value})


def test_mismatch_value_must_equal_extracted_data(
    valid_document_response: dict[str, Any],
    copy_dict: Any,
) -> None:
    response = copy_dict(valid_document_response)
    second = copy_dict(response["documents"][0])
    second["documentId"] = "purchase-order-1"
    second["documentType"] = "PURCHASE_ORDER"
    second["extractedData"]["totalAmount"] = "19000000"
    for evidence in second["sourceEvidence"]:
        evidence["documentId"] = "purchase-order-1"
        evidence["evidenceId"] = f"po-{evidence['evidenceId']}"
    response["documents"].append(second)
    response["mismatches"] = [
        {
            "field": "totalAmount",
            "values": [
                {"documentId": "invoice-1", "value": "777"},
                {"documentId": "purchase-order-1", "value": "888"},
            ],
            "description": "조작된 비교값",
            "sourceEvidenceIds": ["ev-total", "po-ev-total"],
        }
    ]
    response["reviewRequired"] = True

    with pytest.raises(ValidationError, match="must match extractedData"):
        DocumentAnalysisResult.model_validate(response)
