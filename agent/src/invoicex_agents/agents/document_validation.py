"""Deterministic media and source-evidence validation for the Document Agent."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from invoicex_agents.clients.base import MAX_PDF_PAGES, MediaDocument
from invoicex_agents.exceptions import AgentInputError, GeminiResponseValidationError
from invoicex_agents.models.document import (
    DATE_DOCUMENT_FIELDS,
    NUMERIC_DOCUMENT_FIELDS,
    DocumentAnalysisResult,
    DocumentField,
    canonical_date_string,
    canonical_numeric_string,
)

_NUMBER_PATTERN = re.compile(r"(?<!\d)([+-]?(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d+)?)(?!\d)")
_DATE_PATTERN = re.compile(r"(\d{4}\s*(?:[-./]|년)\s*\d{1,2}\s*(?:[-./]|월)\s*\d{1,2}\s*일?)")


@dataclass(frozen=True, slots=True)
class MediaInspection:
    """Safe metadata and locally extractable page text for one media document."""

    page_texts: tuple[str, ...]


def _normalized_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _quote_supports_value(field: DocumentField, value: object, quote: str) -> bool:
    if field in NUMERIC_DOCUMENT_FIELDS:
        for candidate in _NUMBER_PATTERN.findall(unicodedata.normalize("NFKC", quote)):
            try:
                if canonical_numeric_string(candidate) == canonical_numeric_string(value):
                    return True
            except ValueError:
                continue
        return False

    if field in DATE_DOCUMENT_FIELDS:
        for candidate in _DATE_PATTERN.findall(unicodedata.normalize("NFKC", quote)):
            try:
                if canonical_date_string(candidate) == canonical_date_string(value):
                    return True
            except ValueError:
                continue
        return False

    if field is DocumentField.DELIVERY_COMPLETED:
        normalized_quote = _normalized_text(quote)
        false_markers = ("notcompleted", "notaccepted", "미완료", "미검수", "false")
        true_markers = (
            "accepted",
            "completed",
            "delivered",
            "검수완료",
            "납품완료",
            "인수완료",
            "pass",
            "true",
        )
        if value is False:
            return any(marker in normalized_quote for marker in false_markers)
        return not any(marker in normalized_quote for marker in false_markers) and any(
            marker in normalized_quote for marker in true_markers
        )

    return _normalized_text(str(value)) in _normalized_text(quote)


def inspect_media_documents(
    media: tuple[MediaDocument, ...],
) -> dict[str, MediaInspection]:
    """Parse safe media metadata before any external model request."""

    inspections: dict[str, MediaInspection] = {}
    for document in media:
        if document.mime_type != "application/pdf":
            inspections[document.document_id] = MediaInspection(page_texts=("",))
            continue

        try:
            reader = PdfReader(BytesIO(document.data), strict=False)
            if reader.is_encrypted:
                raise AgentInputError("encrypted PDF documents are not supported")
            if not reader.pages:
                raise AgentInputError("PDF documents must contain at least one page")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise AgentInputError(f"PDF documents must not exceed {MAX_PDF_PAGES} pages")
            page_texts = tuple((page.extract_text() or "") for page in reader.pages)
        except AgentInputError:
            raise
        except Exception as exc:
            raise AgentInputError("PDF document could not be parsed safely") from exc
        inspections[document.document_id] = MediaInspection(page_texts=page_texts)
    return inspections


def validate_source_evidence(
    result: DocumentAnalysisResult,
    inspections: dict[str, MediaInspection],
) -> dict[str, set[DocumentField]]:
    """Reject fabricated evidence and flag evidence that cannot be text-verified."""

    review_fields: dict[str, set[DocumentField]] = {
        document.document_id: set() for document in result.documents
    }
    for document in result.documents:
        inspection = inspections[document.document_id]
        for evidence in document.source_evidence:
            field = DocumentField(evidence.field)
            if evidence.page > len(inspection.page_texts):
                raise GeminiResponseValidationError(
                    "sourceEvidence page exceeds the uploaded document page count"
                )

            page_text = inspection.page_texts[evidence.page - 1]
            if page_text:
                if _normalized_text(evidence.quote) not in _normalized_text(page_text):
                    raise GeminiResponseValidationError(
                        "sourceEvidence quote was not found on the referenced PDF page"
                    )
            else:
                review_fields[document.document_id].add(field)

            extracted_value = document.extracted_data.value_for(field)
            if extracted_value is None or not _quote_supports_value(
                field, extracted_value, evidence.quote
            ):
                raise GeminiResponseValidationError(
                    "sourceEvidence quote does not support the extracted field value"
                )
    return review_fields
