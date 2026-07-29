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


@dataclass(frozen=True, slots=True)
class MediaDocument:
    """An in-memory document passed to Gemini without persisting its contents."""

    document_id: str
    mime_type: str
    data: bytes

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise AgentInputError("document_id must not be blank")
        if self.mime_type not in SUPPORTED_DOCUMENT_MIME_TYPES:
            raise AgentInputError(f"unsupported document MIME type: {self.mime_type}")
        if not self.data:
            raise AgentInputError("document data must not be empty")


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
