"""Real/mock client boundary tests without network calls."""

from types import SimpleNamespace
from typing import Any

import pytest

from invoicex_agents.clients.base import MediaDocument
from invoicex_agents.clients.gemini import (
    GoogleGeminiClient,
    _gemini_response_json_schema,
)
from invoicex_agents.clients.mock import StaticGeminiClient
from invoicex_agents.config import AgentSettings
from invoicex_agents.exceptions import (
    AgentConfigurationError,
    GeminiInvocationError,
    GeminiResponseValidationError,
)
from invoicex_agents.models.document import DocumentAnalysisResult


def test_real_client_requires_vertex_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERTEX_AI_PROJECT_ID", raising=False)
    settings = AgentSettings(_env_file=None, VERTEX_AI_PROJECT_ID=None)

    with pytest.raises(AgentConfigurationError, match="VERTEX_AI_PROJECT_ID"):
        GoogleGeminiClient(settings)


def test_real_client_parser_accepts_valid_parsed_payload(
    valid_document_response: dict[str, Any],
) -> None:
    response = SimpleNamespace(parsed=valid_document_response, text=None)

    parsed = GoogleGeminiClient._parse_response(response, DocumentAnalysisResult)

    assert parsed.schema_version == "document-agent.v1"


def test_real_client_parser_rejects_empty_response() -> None:
    response = SimpleNamespace(parsed=None, text=None)

    with pytest.raises(GeminiResponseValidationError, match="no structured"):
        GoogleGeminiClient._parse_response(response, DocumentAnalysisResult)


def test_mock_client_enforces_response_schema() -> None:
    client = StaticGeminiClient({"unexpected": True})

    with pytest.raises(GeminiResponseValidationError, match="Mock response"):
        client.generate_structured(
            system_instruction="system",
            user_prompt="user",
            response_schema=DocumentAnalysisResult,
        )


def test_real_client_builds_structured_media_request(
    monkeypatch: pytest.MonkeyPatch,
    valid_document_response: dict[str, Any],
) -> None:
    captured: dict[str, Any] = {}

    class FakeModels:
        def generate_content(self, **kwargs: Any) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(parsed=valid_document_response, text=None)

    fake_sdk_client = SimpleNamespace(models=FakeModels())

    def fake_client_factory(**kwargs: Any) -> SimpleNamespace:
        captured["client_kwargs"] = kwargs
        return fake_sdk_client

    monkeypatch.setattr(
        "invoicex_agents.clients.gemini.genai.Client",
        fake_client_factory,
    )
    settings = AgentSettings(
        _env_file=None,
        VERTEX_AI_PROJECT_ID="test-project",
        VERTEX_AI_LOCATION="asia-northeast3",
        GEMINI_MODEL="test-model",
    )
    client = GoogleGeminiClient(settings)

    result = client.generate_structured(
        system_instruction="system",
        user_prompt="manifest",
        response_schema=DocumentAnalysisResult,
        media=(
            MediaDocument(
                "invoice-1",
                "image/png",
                b"\x89PNG\r\n\x1a\nsynthetic",
            ),
        ),
    )

    assert result.documents[0].document_id == "invoice-1"
    assert captured["model"] == "test-model"
    assert len(captured["contents"]) == 3
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].response_schema is None
    assert captured["config"].response_json_schema is not None
    assert captured["client_kwargs"] == {
        "vertexai": True,
        "project": "test-project",
        "location": "asia-northeast3",
        "http_options": captured["client_kwargs"]["http_options"],
    }


def test_gemini_schema_normalizes_unsupported_keywords() -> None:
    schema = _gemini_response_json_schema(DocumentAnalysisResult)

    def collect_keys(node: object) -> set[str]:
        if isinstance(node, dict):
            return set(node) | {key for value in node.values() for key in collect_keys(value)}
        if isinstance(node, list):
            return {key for value in node for key in collect_keys(value)}
        return set()

    assert "additionalProperties" not in collect_keys(schema)
    assert "const" not in collect_keys(schema)
    assert schema["properties"]["schemaVersion"]["enum"] == ["document-agent.v1"]


def test_real_client_wraps_transport_error_without_raw_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TransportError(Exception):
        status_code = 400

    class FailingModels:
        def generate_content(self, **kwargs: Any) -> None:
            raise TransportError("request contained secret test-key")

    monkeypatch.setattr(
        "invoicex_agents.clients.gemini.genai.Client",
        lambda **kwargs: SimpleNamespace(models=FailingModels()),
    )
    settings = AgentSettings(_env_file=None, VERTEX_AI_PROJECT_ID="test-project")
    client = GoogleGeminiClient(settings)

    with pytest.raises(GeminiInvocationError, match="TransportError") as caught:
        client.generate_structured(
            system_instruction="system",
            user_prompt="user",
            response_schema=DocumentAnalysisResult,
        )

    assert "test-key" not in str(caught.value)


def test_real_client_retries_only_retryable_status(
    monkeypatch: pytest.MonkeyPatch,
    valid_document_response: dict[str, Any],
) -> None:
    class RateLimitError(Exception):
        status_code = 429

    class RetryModels:
        calls = 0

        def generate_content(self, **kwargs: Any) -> SimpleNamespace:
            self.calls += 1
            if self.calls == 1:
                raise RateLimitError("retry")
            return SimpleNamespace(parsed=valid_document_response, text=None)

    models = RetryModels()
    monkeypatch.setattr(
        "invoicex_agents.clients.gemini.genai.Client",
        lambda **kwargs: SimpleNamespace(models=models),
    )
    monkeypatch.setattr("invoicex_agents.clients.gemini.time.sleep", lambda _: None)
    settings = AgentSettings(
        _env_file=None,
        VERTEX_AI_PROJECT_ID="test-project",
        GEMINI_MAX_ATTEMPTS=2,
    )
    client = GoogleGeminiClient(settings)

    result = client.generate_structured(
        system_instruction="system",
        user_prompt="user",
        response_schema=DocumentAnalysisResult,
    )

    assert result.schema_version == "document-agent.v1"
    assert models.calls == 2
