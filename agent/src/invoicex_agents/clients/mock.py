"""Deterministic structured client for tests and local backend development."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from invoicex_agents.clients.base import MediaDocument, StructuredModel
from invoicex_agents.exceptions import GeminiResponseValidationError

MockResponse = dict[str, Any] | BaseModel
MockResponseFactory = Callable[[type[BaseModel]], MockResponse]


class StaticGeminiClient:
    """Return one configured response while still enforcing the real schema."""

    def __init__(self, response: MockResponse | MockResponseFactory) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def generate_structured(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        response_schema: type[StructuredModel],
        media: tuple[MediaDocument, ...] = (),
    ) -> StructuredModel:
        self.calls.append(
            {
                "system_instruction": system_instruction,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "media_document_ids": tuple(item.document_id for item in media),
            }
        )
        raw_response = (
            self._response(response_schema) if callable(self._response) else self._response
        )
        try:
            if isinstance(raw_response, response_schema):
                return raw_response
            if isinstance(raw_response, BaseModel):
                raw_response = raw_response.model_dump(by_alias=True)
            return response_schema.model_validate(raw_response)
        except ValidationError as exc:
            raise GeminiResponseValidationError(
                "Mock response failed structured-output validation"
            ) from exc
