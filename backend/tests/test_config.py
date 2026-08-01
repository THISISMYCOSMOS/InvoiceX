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


def test_funding_mode_does_not_require_settlement_wallets() -> None:
    settings = BackendSettings(
        _env_file=None,
        SOLANA_MODE="auto",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
    )

    assert settings.resolved_solana_mode() == "privy"
    assert settings.solana_demo_transfer_amount_usdc == 1
    assert settings.missing_privy_funding_configuration() == []
    assert settings.missing_privy_settlement_configuration()
