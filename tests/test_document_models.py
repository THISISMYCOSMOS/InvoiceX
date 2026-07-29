"""Document Agent schema invariant tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from invoicex_agents.models.document import DocumentAnalysisResult


def test_valid_document_result_is_accepted(
    valid_document_response: dict[str, Any],
) -> None:
    result = DocumentAnalysisResult.model_validate(valid_document_response)

    assert result.documents[0].extracted_data.invoice_number == "INV-2026-001"
    assert result.review_required is False


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
