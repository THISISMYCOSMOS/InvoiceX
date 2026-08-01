from __future__ import annotations

import pytest
from pydantic import ValidationError

from invoicex_backend.config import BackendSettings


def test_solana_defaults_to_devnet() -> None:
    settings = BackendSettings(_env_file=None)

    assert settings.solana_cluster == "devnet"
    assert settings.resolved_rpc_url() == "https://api.devnet.solana.com"
    assert settings.resolved_caip2() == "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1"
    assert settings.solana_network_name() == "SOLANA_DEVNET"
    assert settings.solana_demo_transfer_amount_usdc == 1


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


def test_auto_privy_funding_requires_only_treasury_credentials_on_devnet() -> None:
    settings = BackendSettings(
        _env_file=None,
        SOLANA_MODE="auto",
        SOLANA_CLUSTER="devnet",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_WALLET_ID="treasury-wallet-id",
    )

    assert settings.resolved_solana_mode() == "privy"
    assert settings.missing_privy_settlement_configuration() == [
        "PRIVY_SETTLEMENT_WALLET_ID",
        "INVESTOR_SETTLEMENT_WALLET_ADDRESS",
        "PLATFORM_FEE_WALLET_ADDRESS",
    ]


def test_testnet_does_not_treat_the_circle_devnet_mint_as_real_ready() -> None:
    settings = BackendSettings(
        _env_file=None,
        SOLANA_MODE="auto",
        SOLANA_CLUSTER="testnet",
        PRIVY_APP_ID="app-id",
        PRIVY_APP_SECRET="app-secret",
        PRIVY_WALLET_ID="treasury-wallet-id",
    )

    assert settings.resolved_solana_mode() == "mock"
    assert "SOLANA_USDC_MINT (testnet-compatible SPL token)" in (
        settings.missing_privy_configuration()
    )
