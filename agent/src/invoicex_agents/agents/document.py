"""Document Agent orchestration and input/output boundary validation."""

from __future__ import annotations

import json
from collections.abc import Sequence

from invoicex_agents.agents._prompts import load_prompt
from invoicex_agents.agents.document_validation import (
    inspect_media_documents,
    validate_source_evidence,
)
from invoicex_agents.clients.base import (
    MAX_DOCUMENTS_PER_ANALYSIS,
    MAX_TOTAL_DOCUMENT_BYTES,
    MediaDocument,
    StructuredOutputClient,
)
from invoicex_agents.exceptions import AgentInputError, GeminiResponseValidationError
from invoicex_agents.models.document import DocumentAnalysisResult


class DocumentAgent:
    """Analyze supplied documents without persisting files or workflow state."""

    def __init__(self, client: StructuredOutputClient) -> None:
        self._client = client
        self._system_instruction = load_prompt("document_agent.md")

    def analyze(self, documents: Sequence[MediaDocument]) -> DocumentAnalysisResult:
        """Return a fully grounded structured analysis for the document set."""

        media = tuple(documents)
        if not media:
            raise AgentInputError("at least one document is required")
        if len(media) > MAX_DOCUMENTS_PER_ANALYSIS:
            raise AgentInputError(
                f"no more than {MAX_DOCUMENTS_PER_ANALYSIS} documents may be analyzed"
            )
        if sum(len(item.data) for item in media) > MAX_TOTAL_DOCUMENT_BYTES:
            raise AgentInputError(
                f"combined document data exceeds the {MAX_TOTAL_DOCUMENT_BYTES}-byte limit"
            )

        input_ids = [item.document_id for item in media]
        if len(input_ids) != len(set(input_ids)):
            raise AgentInputError("document_id values must be unique")
        inspections = inspect_media_documents(media)

        manifest = {
            "documents": [
                {
                    "documentId": document.document_id,
                    "mimeType": document.mime_type,
                }
                for document in media
            ],
            "task": (
                "Analyze every supplied document, compare shared fields, and return one "
                "document-agent.v1 result. Use the backend documentId values exactly."
            ),
        }
        result = self._client.generate_structured(
            system_instruction=self._system_instruction,
            user_prompt=json.dumps(manifest, ensure_ascii=False),
            response_schema=DocumentAnalysisResult,
            media=media,
        )

        output_ids = [item.document_id for item in result.documents]
        if set(output_ids) != set(input_ids):
            raise GeminiResponseValidationError(
                "Document Agent output must contain exactly the supplied documentId values"
            )
        review_fields = validate_source_evidence(result, inspections)
        return result.reconciled(extra_review_fields=review_fields)
