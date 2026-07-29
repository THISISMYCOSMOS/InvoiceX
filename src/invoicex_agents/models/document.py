"""Structured output and invariants for the Document Agent."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from invoicex_agents.models.common import SourceEvidence, StrictModel


class DocumentType(StrEnum):
    """Internal document classifications supported by the first MVP slice."""

    INVOICE = "INVOICE"
    CONTRACT = "CONTRACT"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    DELIVERY_EVIDENCE = "DELIVERY_EVIDENCE"
    INSPECTION_CERTIFICATE = "INSPECTION_CERTIFICATE"
    TRANSACTION_STATEMENT = "TRANSACTION_STATEMENT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class DocumentField(StrEnum):
    """Fields explicitly requested by the InvoiceX product documents."""

    INVOICE_NUMBER = "invoiceNumber"
    SUPPLIER_NAME = "supplierName"
    BUYER_NAME = "buyerName"
    PURCHASE_ORDER_NUMBER = "purchaseOrderNumber"
    CONTRACT_NUMBER = "contractNumber"
    CURRENCY = "currency"
    TOTAL_AMOUNT = "totalAmount"
    ISSUE_DATE = "issueDate"
    DUE_DATE = "dueDate"
    ITEM_NAME = "itemName"
    QUANTITY = "quantity"
    UNIT_PRICE = "unitPrice"
    PAYMENT_TERMS = "paymentTerms"
    DELIVERY_COMPLETED = "deliveryCompleted"


class DocumentExtractedData(StrictModel):
    """Normalized fields extracted from one source document."""

    invoice_number: str | None = Field(default=None, max_length=200)
    supplier_name: str | None = Field(default=None, max_length=300)
    buyer_name: str | None = Field(default=None, max_length=300)
    purchase_order_number: str | None = Field(default=None, max_length=200)
    contract_number: str | None = Field(default=None, max_length=200)
    currency: str | None = Field(default=None, max_length=10)
    total_amount: str | None = Field(default=None, max_length=100)
    issue_date: str | None = Field(default=None, max_length=50)
    due_date: str | None = Field(default=None, max_length=50)
    item_name: str | None = Field(default=None, max_length=500)
    quantity: str | None = Field(default=None, max_length=100)
    unit_price: str | None = Field(default=None, max_length=100)
    payment_terms: str | None = Field(default=None, max_length=500)
    delivery_completed: bool | None = None

    def populated_fields(self) -> set[str]:
        """Return aliases of fields that contain document-supported values."""

        populated: set[str] = set()
        for field_name, field_info in type(self).model_fields.items():
            if getattr(self, field_name) is not None:
                populated.add(field_info.alias or field_name)
        return populated

    def empty_fields(self) -> set[str]:
        """Return aliases of fields whose values are unknown."""

        empty: set[str] = set()
        for field_name, field_info in type(self).model_fields.items():
            if getattr(self, field_name) is None:
                empty.add(field_info.alias or field_name)
        return empty


class AnalyzedDocument(StrictModel):
    """Analysis of a single uploaded source document."""

    document_id: str = Field(min_length=1, max_length=100)
    document_type: DocumentType
    extracted_data: DocumentExtractedData
    missing_fields: list[DocumentField] = Field(default_factory=list)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_and_missing_fields(self) -> AnalyzedDocument:
        evidence_ids = [item.evidence_id for item in self.source_evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("sourceEvidence evidenceId values must be unique")

        for evidence in self.source_evidence:
            if evidence.document_id != self.document_id:
                raise ValueError("sourceEvidence documentId must match its analyzed document")

        evidence_fields = {item.field for item in self.source_evidence}
        fields_without_evidence = self.extracted_data.populated_fields() - evidence_fields
        if fields_without_evidence:
            missing = ", ".join(sorted(fields_without_evidence))
            raise ValueError(f"non-null extracted fields require sourceEvidence: {missing}")

        declared_missing = {field.value for field in self.missing_fields}
        if len(declared_missing) != len(self.missing_fields):
            raise ValueError("missingFields values must be unique")

        empty_field_aliases = self.extracted_data.empty_fields()
        invalid_missing = declared_missing - empty_field_aliases
        if invalid_missing:
            invalid = ", ".join(sorted(invalid_missing))
            raise ValueError(f"missingFields must have null extracted values: {invalid}")

        undeclared_empty = empty_field_aliases - declared_missing
        if undeclared_empty:
            undeclared = ", ".join(sorted(undeclared_empty))
            raise ValueError(
                f"every null extracted field must be listed in missingFields: {undeclared}"
            )

        return self


class MismatchValue(StrictModel):
    """A document-specific value participating in a mismatch."""

    document_id: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)


class Mismatch(StrictModel):
    """A disagreement between at least two uploaded documents."""

    field: DocumentField
    values: list[MismatchValue] = Field(min_length=2)
    description: str = Field(min_length=1, max_length=1000)
    source_evidence_ids: list[str] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_unique_references(self) -> Mismatch:
        document_ids = [item.document_id for item in self.values]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("mismatch values must reference distinct documents")
        if len(self.source_evidence_ids) != len(set(self.source_evidence_ids)):
            raise ValueError("mismatch sourceEvidenceIds must be unique")
        return self


class DocumentAnalysisResult(StrictModel):
    """Complete, evidence-backed result for a group of transaction documents."""

    schema_version: Literal["document-agent.v1"] = "document-agent.v1"
    documents: list[AnalyzedDocument] = Field(min_length=1)
    mismatches: list[Mismatch] = Field(default_factory=list)
    review_required: bool

    @model_validator(mode="after")
    def validate_cross_document_invariants(self) -> DocumentAnalysisResult:
        document_ids = [item.document_id for item in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("documents must contain unique documentId values")
        known_document_ids = set(document_ids)

        evidence_by_id: dict[str, SourceEvidence] = {}
        for document in self.documents:
            for evidence in document.source_evidence:
                if evidence.evidence_id in evidence_by_id:
                    raise ValueError("evidenceId values must be unique across all documents")
                evidence_by_id[evidence.evidence_id] = evidence

        for mismatch in self.mismatches:
            mismatch_document_ids = {item.document_id for item in mismatch.values}
            if not mismatch_document_ids <= known_document_ids:
                raise ValueError("mismatch references an unknown documentId")

            referenced_evidence = []
            for evidence_id in mismatch.source_evidence_ids:
                evidence = evidence_by_id.get(evidence_id)
                if evidence is None:
                    raise ValueError("mismatch references an unknown sourceEvidenceId")
                referenced_evidence.append(evidence)

            if {item.document_id for item in referenced_evidence} != mismatch_document_ids:
                raise ValueError("mismatch evidence must cover every mismatched document")
            if any(item.field != mismatch.field.value for item in referenced_evidence):
                raise ValueError("mismatch evidence field must match the mismatch field")

        if self.mismatches and not self.review_required:
            raise ValueError("reviewRequired must be true when documents disagree")

        return self
