"""Google AI Studio Gemini implementation."""

from __future__ import annotations

import time

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from invoicex_agents.clients.base import MediaDocument, StructuredModel
from invoicex_agents.config import AgentSettings
from invoicex_agents.exceptions import (
    AgentConfigurationError,
    GeminiInvocationError,
    GeminiResponseValidationError,
)

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def _gemini_response_json_schema(response_schema: type[BaseModel]) -> dict[str, object]:
    """Return a Gemini-compatible schema while keeping strict local validation."""

    schema = response_schema.model_json_schema(by_alias=True)

    def remove_unsupported_keywords(node: object) -> None:
        if isinstance(node, dict):
            node.pop("additionalProperties", None)
            if "const" in node and "enum" not in node:
                node["enum"] = [node.pop("const")]
            for value in node.values():
                remove_unsupported_keywords(value)
        elif isinstance(node, list):
            for value in node:
                remove_unsupported_keywords(value)

    remove_unsupported_keywords(schema)
    return schema


class GoogleGeminiClient:
    """Structured-output Gemini client authenticated with an AI Studio API key."""

    def __init__(self, settings: AgentSettings | None = None) -> None:
        self._settings = settings or AgentSettings()
        api_key = self._settings.gemini_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise AgentConfigurationError("GEMINI_API_KEY is required for the real Gemini client")

        self._client = genai.Client(
            api_key=api_key.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=int(self._settings.gemini_timeout_seconds * 1000)
            ),
        )

    def generate_structured(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        media: tuple[MediaDocument, ...] = (),
    ) -> BaseModel:
        """Call Gemini and reject any response that does not match the schema."""

        contents: list[types.Part] = []
        for document in media:
            contents.append(
                types.Part.from_text(
                    text=(
                        f"The next untrusted file has backend documentId {document.document_id!r}."
                    )
                )
            )
            contents.append(types.Part.from_bytes(data=document.data, mime_type=document.mime_type))
        contents.append(types.Part.from_text(text=user_prompt))

        last_error: Exception | None = None
        last_status_code: object | None = None
        for attempt in range(1, self._settings.gemini_max_attempts + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_json_schema=_gemini_response_json_schema(response_schema),
                        temperature=0,
                    ),
                )
                return self._parse_response(response, response_schema)
            except GeminiResponseValidationError:
                raise
            except Exception as exc:  # SDK transports expose different concrete errors.
                last_error = exc
                status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                last_status_code = status_code
                should_retry = (
                    attempt < self._settings.gemini_max_attempts
                    and status_code in _RETRYABLE_STATUS_CODES
                )
                if not should_retry:
                    break
                time.sleep(0.5 * (2 ** (attempt - 1)))

        error_type = type(last_error).__name__ if last_error is not None else "UnknownError"
        status_label = last_status_code if last_status_code is not None else "unknown"
        raise GeminiInvocationError(
            f"Gemini request failed (status={status_label}, type={error_type})",
            status_code=last_status_code,
            retryable=last_status_code in _RETRYABLE_STATUS_CODES,
        ) from None

    @staticmethod
    def _parse_response(
        response: object,
        response_schema: type[StructuredModel],
    ) -> StructuredModel:
        parsed = getattr(response, "parsed", None)
        try:
            if isinstance(parsed, response_schema):
                return parsed
            if parsed is not None:
                return response_schema.model_validate(parsed)

            response_text = getattr(response, "text", None)
            if not response_text:
                raise GeminiResponseValidationError("Gemini returned no structured response")
            return response_schema.model_validate_json(response_text)
        except ValidationError as exc:
            raise GeminiResponseValidationError(
                "Gemini response failed structured-output validation"
            ) from exc
