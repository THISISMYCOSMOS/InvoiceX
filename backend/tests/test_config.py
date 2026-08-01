from __future__ import annotations

import pytest
from pydantic import ValidationError
from solders.keypair import Keypair
from solders.pubkey import Pubkey

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


def test_auto_mode_prefers_complete_privy_configuration() -> None:
    settings = BackendSettings(
        _env_file=None,
        SOLANA_MODE="auto",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_TREASURY_WALLET_ID="treasury",
        PRIVY_RWA_ISSUER_WALLET_ID="issuer",
        PRIVY_TREASURY_WALLET_ADDRESS=str(Pubkey.new_unique()),
    )
    assert settings.resolved_solana_mode() == "privy"


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


def test_direct_mode_requires_keys_and_selects_direct_when_configured() -> None:
    with pytest.raises(ValidationError, match="SOLANA_MODE=direct"):
        BackendSettings(_env_file=None, SOLANA_MODE="direct")

    settings = BackendSettings(
        _env_file=None,
        SOLANA_MODE="direct",
        SOLANA_PLATFORM_KEYPAIR=str(Keypair()),
        SOLANA_AGENT_VAULT_KEYPAIR=str(Keypair()),
        DEMO_STABLECOIN_MINT=str(Pubkey.new_unique()),
    )
    assert settings.resolved_solana_mode() == "direct"
