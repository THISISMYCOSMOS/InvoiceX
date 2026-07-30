from __future__ import annotations

import pytest
from pydantic import ValidationError

from invoicex_backend.config import BackendSettings


def test_auto_modes_use_mock_without_external_credentials() -> None:
    settings = BackendSettings(
        _env_file=None,
        AGENT_MODE="auto",
        SOLANA_MODE="auto",
        GEMINI_API_KEY="",
        PRIVY_APP_ID="",
        PRIVY_APP_SECRET="",
    )
    assert settings.resolved_agent_mode() == "mock"
    assert settings.resolved_solana_mode() == "mock"


def test_explicit_real_agent_requires_gemini_key() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        BackendSettings(
            _env_file=None,
            AGENT_MODE="real",
            GEMINI_API_KEY="",
        )


def test_explicit_privy_mode_requires_complete_configuration() -> None:
    with pytest.raises(ValidationError, match="SOLANA_MODE=privy"):
        BackendSettings(
            _env_file=None,
            SOLANA_MODE="privy",
            PRIVY_APP_ID="",
            PRIVY_APP_SECRET="",
        )
