"""Structured output and invariants for the Document Agent."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

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


NUMERIC_DOCUMENT_FIELDS = frozenset(
    {
        DocumentField.TOTAL_AMOUNT,
        DocumentField.QUANTITY,
        DocumentField.UNIT_PRICE,
    }
)
DATE_DOCUMENT_FIELDS = frozenset(
    {
        DocumentField.ISSUE_DATE,
        DocumentField.DUE_DATE,
    }
)
IDENTIFIER_DOCUMENT_FIELDS = frozenset(
    {
        DocumentField.INVOICE_NUMBER,
        DocumentField.PURCHASE_ORDER_NUMBER,
        DocumentField.CONTRACT_NUMBER,
    }
)
COMPARABLE_DOCUMENT_FIELDS = (
    DocumentField.INVOICE_NUMBER,
    DocumentField.SUPPLIER_NAME,
    DocumentField.BUYER_NAME,
    DocumentField.PURCHASE_ORDER_NUMBER,
    DocumentField.CONTRACT_NUMBER,
    DocumentField.CURRENCY,
    DocumentField.TOTAL_AMOUNT,
    DocumentField.DUE_DATE,
    DocumentField.ITEM_NAME,
    DocumentField.QUANTITY,
    DocumentField.UNIT_PRICE,
    DocumentField.DELIVERY_COMPLETED,
)
REQUIRED_FIELDS_BY_DOCUMENT_TYPE = {
    DocumentType.INVOICE: frozenset(
        {
            DocumentField.INVOICE_NUMBER,
            DocumentField.SUPPLIER_NAME,
            DocumentField.BUYER_NAME,
            DocumentField.CURRENCY,
            DocumentField.TOTAL_AMOUNT,
            DocumentField.ISSUE_DATE,
            DocumentField.DUE_DATE,
        }
    ),
    DocumentType.CONTRACT: frozenset(
        {
            DocumentField.SUPPLIER_NAME,
            DocumentField.BUYER_NAME,
            DocumentField.CONTRACT_NUMBER,
            DocumentField.PAYMENT_TERMS,
        }
    ),
    DocumentType.PURCHASE_ORDER: frozenset(
        {
            DocumentField.SUPPLIER_NAME,
            DocumentField.BUYER_NAME,
            DocumentField.PURCHASE_ORDER_NUMBER,
            DocumentField.CURRENCY,
            DocumentField.TOTAL_AMOUNT,
            DocumentField.ISSUE_DATE,
            DocumentField.ITEM_NAME,
            DocumentField.QUANTITY,
            DocumentField.UNIT_PRICE,
        }
    ),
    DocumentType.DELIVERY_EVIDENCE: frozenset(
        {
            DocumentField.SUPPLIER_NAME,
            DocumentField.BUYER_NAME,
            DocumentField.PURCHASE_ORDER_NUMBER,
            DocumentField.ITEM_NAME,
            DocumentField.QUANTITY,
            DocumentField.DELIVERY_COMPLETED,
        }
    ),
}
_DOCUMENT_FIELD_ORDER = {field: index for index, field in enumerate(DocumentField)}
_NUMBER_PATTERN = re.compile(r"(?<!\d)([+-]?(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d+)?)(?!\d)")
_DATE_PATTERN = re.compile(
    r"^\s*(\d{4})\s*(?:[-./]|년)\s*(\d{1,2})\s*"
    r"(?:[-./]|월)\s*(\d{1,2})\s*일?\s*$"
)


def canonical_numeric_string(value: object) -> str:
    """Return a positive decimal string without separators or unit labels."""

    if isinstance(value, bool):
        raise ValueError("boolean values are not valid numeric document fields")
    source = unicodedata.normalize("NFKC", str(value)).strip()
    matches = _NUMBER_PATTERN.findall(source)
    if len(matches) != 1:
        raise ValueError("numeric document fields must contain exactly one number")
    try:
        number = Decimal(matches[0].replace(",", "").replace(" ", ""))
    except InvalidOperation as exc:
        raise ValueError("numeric document field is not a valid decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("numeric document fields must be positive and finite")
    canonical = format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    return canonical


def canonical_date_string(value: object) -> str:
    """Return an ISO date after validating a supported explicit date form."""

    source = unicodedata.normalize("NFKC", str(value))
    match = _DATE_PATTERN.fullmatch(source)
    if match is None:
        raise ValueError("date document fields must use an explicit calendar date")
    parsed = date(*(int(part) for part in match.groups()))
    return parsed.isoformat()


def canonical_currency_code(value: object) -> str:
    """Return an uppercase currency or settlement-asset code."""

    source = unicodedata.normalize("NFKC", str(value)).strip().upper()
    aliases = {"원": "KRW", "₩": "KRW"}
    source = aliases.get(source, source)
    if re.fullmatch(r"(?:[A-Z]{3}|USDC)", source) is None:
        raise ValueError("currency must be a three-letter code or USDC")
    return source


def canonical_identifier_string(value: object) -> str:
    """Remove OCR whitespace around common identifier separators."""

    source = unicodedata.normalize("NFKC", str(value)).strip()
    source = re.sub(r"[\u2010-\u2015\u2212]", "-", source)
    source = re.sub(r"\s*([-/])\s*", r"\1", source)
    return re.sub(r"\s+", " ", source)


def normalize_comparison_value(field: DocumentField, value: object) -> str:
    """Return a deterministic field-specific value used for comparisons."""

    if field in NUMERIC_DOCUMENT_FIELDS:
        return canonical_numeric_string(value)
    if field in DATE_DOCUMENT_FIELDS:
        return canonical_date_string(value)
    if field is DocumentField.CURRENCY:
        return canonical_currency_code(value)
    if field in IDENTIFIER_DOCUMENT_FIELDS:
        value = canonical_identifier_string(value)
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return "".join(character for character in normalized if character.isalnum())


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

    @field_validator("total_amount", "quantity", "unit_price", mode="before")
    @classmethod
    def normalize_numeric_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        return canonical_numeric_string(value)

    @field_validator("issue_date", "due_date", mode="before")
    @classmethod
    def normalize_date_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        return canonical_date_string(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: Any) -> Any:
        if value is None:
            return None
        return canonical_currency_code(value)

    @field_validator(
        "invoice_number",
        "purchase_order_number",
        "contract_number",
        mode="before",
    )
    @classmethod
    def normalize_identifiers(cls, value: Any) -> Any:
        if value is None:
            return None
        return canonical_identifier_string(value)

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

    def value_for(self, field: DocumentField) -> object | None:
        """Return a value by its public camelCase document field name."""

        for field_name, field_info in type(self).model_fields.items():
            if (field_info.alias or field_name) == field.value:
                return getattr(self, field_name)
        raise KeyError(field.value)


class AnalyzedDocument(StrictModel):
    """Analysis of a single uploaded source document."""

    document_id: str = Field(min_length=1, max_length=100)
    document_type: DocumentType
    extracted_data: DocumentExtractedData
    missing_fields: list[DocumentField] = Field(default_factory=list)
    review_fields: list[DocumentField] = Field(default_factory=list)
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
        known_fields = {field.value for field in DocumentField}
        invalid_evidence_fields = evidence_fields - known_fields
        if invalid_evidence_fields:
            invalid = ", ".join(sorted(invalid_evidence_fields))
            raise ValueError(f"sourceEvidence contains unknown document fields: {invalid}")

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

        evidence_for_empty_fields = evidence_fields & empty_field_aliases
        if evidence_for_empty_fields:
            invalid = ", ".join(sorted(evidence_for_empty_fields))
            raise ValueError(f"sourceEvidence cannot target null extracted fields: {invalid}")

        if len(set(self.review_fields)) != len(self.review_fields):
            raise ValueError("reviewFields values must be unique")

        return self

    def required_missing_fields(self) -> set[DocumentField]:
        """Return workflow-critical fields absent from this document type."""

        required = REQUIRED_FIELDS_BY_DOCUMENT_TYPE.get(self.document_type, frozenset())
        return {field for field in required if self.extracted_data.value_for(field) is None}


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


def build_deterministic_mismatches(
    documents: list[AnalyzedDocument],
) -> list[Mismatch]:
    """Compare normalized shared values without relying on model judgment."""

    mismatches: list[Mismatch] = []
    for field in COMPARABLE_DOCUMENT_FIELDS:
        values: list[MismatchValue] = []
        evidence_ids: list[str] = []
        normalized_values: set[str] = set()
        for document in documents:
            value = document.extracted_data.value_for(field)
            if value is None:
                continue
            evidence = next(item for item in document.source_evidence if item.field == field.value)
            values.append(
                MismatchValue(
                    document_id=document.document_id,
                    value=str(value),
                )
            )
            evidence_ids.append(evidence.evidence_id)
            normalized_values.add(normalize_comparison_value(field, value))

        if len(values) >= 2 and len(normalized_values) >= 2:
            mismatches.append(
                Mismatch(
                    field=field,
                    values=values,
                    description=(
                        f"Normalized {field.value} values differ across {len(values)} documents."
                    ),
                    source_evidence_ids=evidence_ids,
                )
            )
    return mismatches


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
        documents_by_id = {item.document_id: item for item in self.documents}

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
            for mismatch_value in mismatch.values:
                extracted_value = documents_by_id[
                    mismatch_value.document_id
                ].extracted_data.value_for(mismatch.field)
                if extracted_value is None:
                    raise ValueError("mismatch cannot reference a null extracted value")
                if normalize_comparison_value(
                    mismatch.field, mismatch_value.value
                ) != normalize_comparison_value(mismatch.field, extracted_value):
                    raise ValueError("mismatch value must match extractedData")

        if self.mismatches and not self.review_required:
            raise ValueError("reviewRequired must be true when documents disagree")

        return self

    def reconciled(
        self,
        *,
        extra_review_fields: dict[str, set[DocumentField]] | None = None,
    ) -> DocumentAnalysisResult:
        """Return a result with code-derived mismatches and review requirements."""

        deterministic_mismatches = build_deterministic_mismatches(self.documents)
        mismatch_fields_by_document: dict[str, set[DocumentField]] = {
            document.document_id: set() for document in self.documents
        }
        for mismatch in deterministic_mismatches:
            for value in mismatch.values:
                mismatch_fields_by_document[value.document_id].add(mismatch.field)

        reviewed_documents: list[AnalyzedDocument] = []
        for document in self.documents:
            review_fields = (
                set(document.review_fields)
                | document.required_missing_fields()
                | mismatch_fields_by_document[document.document_id]
                | (extra_review_fields or {}).get(document.document_id, set())
            )
            reviewed_documents.append(
                document.model_copy(
                    update={
                        "review_fields": sorted(
                            review_fields,
                            key=_DOCUMENT_FIELD_ORDER.__getitem__,
                        )
                    }
                )
            )

        review_required = bool(
            self.review_required
            or deterministic_mismatches
            or any(document.review_fields for document in reviewed_documents)
        )
        payload = self.model_dump(by_alias=True)
        payload["documents"] = [
            document.model_dump(by_alias=True) for document in reviewed_documents
        ]
        payload["mismatches"] = [
            mismatch.model_dump(by_alias=True) for mismatch in deterministic_mismatches
        ]
        payload["reviewRequired"] = review_required
        return type(self).model_validate(payload)
