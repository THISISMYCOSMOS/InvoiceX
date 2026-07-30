"""Provider-neutral structured generation interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from invoicex_agents.exceptions import AgentInputError

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)

SUPPORTED_DOCUMENT_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_DOCUMENTS_PER_ANALYSIS = 10
MAX_TOTAL_DOCUMENT_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 25


def _matches_declared_mime_type(mime_type: str, data: bytes) -> bool:
    """Return whether the leading bytes match the declared supported media type."""

    if mime_type == "application/pdf":
        return b"%PDF-" in data[:1024]
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


@dataclass(frozen=True, slots=True)
class MediaDocument:
    """An in-memory document passed to Gemini without persisting its contents."""

    document_id: str
    mime_type: str
    data: bytes

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise AgentInputError("document_id must not be blank")
        if len(self.document_id) > 100:
            raise AgentInputError("document_id must not exceed 100 characters")
        if self.mime_type not in SUPPORTED_DOCUMENT_MIME_TYPES:
            raise AgentInputError(f"unsupported document MIME type: {self.mime_type}")
        if not self.data:
            raise AgentInputError("document data must not be empty")
        if len(self.data) > MAX_DOCUMENT_BYTES:
            raise AgentInputError(f"document data exceeds the {MAX_DOCUMENT_BYTES}-byte size limit")
        if not _matches_declared_mime_type(self.mime_type, self.data):
            raise AgentInputError("document bytes do not match the declared MIME type")


class StructuredOutputClient(Protocol):
    """Interface shared by the real Gemini and deterministic mock clients."""

    def generate_structured(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        response_schema: type[StructuredModel],
        media: tuple[MediaDocument, ...] = (),
    ) -> StructuredModel:
        """Generate and validate one structured result."""
