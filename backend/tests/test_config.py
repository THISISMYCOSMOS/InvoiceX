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


def test_backend_exposes_agent_retry_settings() -> None:
    settings = BackendSettings(
        _env_file=None,
        GEMINI_TIMEOUT_SECONDS=90,
        GEMINI_MAX_ATTEMPTS=3,
    )
    assert settings.gemini_timeout_seconds == 90
    assert settings.gemini_max_attempts == 3


def test_explicit_privy_mode_requires_complete_configuration() -> None:
    with pytest.raises(ValidationError, match="SOLANA_MODE=privy"):
        BackendSettings(
            _env_file=None,
            SOLANA_MODE="privy",
            PRIVY_APP_ID="",
            PRIVY_APP_SECRET="",
        )


def test_gasless_mode_requires_a_separate_privy_sponsor_wallet() -> None:
    with pytest.raises(ValidationError, match="GASLESS_ENABLED"):
        BackendSettings(
            _env_file=None,
            SOLANA_MODE="privy",
            GASLESS_ENABLED=True,
            PRIVY_APP_ID="app-id",
            PRIVY_APP_SECRET="app-secret",
            PRIVY_TREASURY_WALLET_ID="treasury",
            PRIVY_RWA_ISSUER_WALLET_ID="issuer",
            PRIVY_TREASURY_WALLET_ADDRESS=str(Pubkey.new_unique()),
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


def test_gcp_target_requires_managed_persistence_and_storage() -> None:
    with pytest.raises(ValidationError, match="DEPLOYMENT_TARGET=gcp"):
        BackendSettings(_env_file=None, DEPLOYMENT_TARGET="gcp")

    settings = BackendSettings(
        _env_file=None,
        DEPLOYMENT_TARGET="gcp",
        PERSISTENCE_BACKEND="cloud_sql",
        DOCUMENT_STORAGE_BACKEND="gcs",
        API_AUTH_REQUIRED=True,
        AUTH_TOKEN_SECRET="test-token-secret-that-is-long-enough-for-hmac",
        MOCK_SETTLEMENT_ENABLED=False,
        GCP_PROJECT_ID="invoicex-demo",
        CLOUD_SQL_INSTANCE_CONNECTION_NAME="invoicex-demo:asia-northeast3:invoicex",
        CLOUD_SQL_DATABASE="invoicex",
        CLOUD_SQL_USER="invoicex_app",
        CLOUD_SQL_PASSWORD="cloud-sql-password-from-secret-manager",
        GCS_DOCUMENT_BUCKET="invoicex-demo-documents",
        GCS_SIGNING_SERVICE_ACCOUNT="invoicex-api@invoicex-demo.iam.gserviceaccount.com",
    )
    assert settings.persistence_backend == "cloud_sql"
    assert settings.document_storage_backend == "gcs"


def test_api_auth_refuses_the_local_default_token_secret() -> None:
    with pytest.raises(ValidationError, match="non-default AUTH_TOKEN_SECRET"):
        BackendSettings(_env_file=None, API_AUTH_REQUIRED=True)


def test_mock_settlement_can_be_disabled_for_the_gcp_auto_investment_scope() -> None:
    settings = BackendSettings(_env_file=None, MOCK_SETTLEMENT_ENABLED=False)
    assert settings.mock_settlement_enabled is False


def test_gcp_mock_settlement_requires_its_separate_wallets() -> None:
    with pytest.raises(ValidationError, match="GCP mock settlement"):
        BackendSettings(
            _env_file=None,
            DEPLOYMENT_TARGET="gcp",
            PERSISTENCE_BACKEND="cloud_sql",
            DOCUMENT_STORAGE_BACKEND="gcs",
            API_AUTH_REQUIRED=True,
            AUTH_TOKEN_SECRET="test-token-secret-that-is-long-enough-for-hmac",
            GCP_PROJECT_ID="invoicex-demo",
            CLOUD_SQL_INSTANCE_CONNECTION_NAME="invoicex-demo:asia-northeast3:invoicex",
            CLOUD_SQL_DATABASE="invoicex",
            CLOUD_SQL_USER="invoicex_app",
            CLOUD_SQL_PASSWORD="cloud-sql-password-from-secret-manager",
            GCS_DOCUMENT_BUCKET="invoicex-demo-documents",
            GCS_SIGNING_SERVICE_ACCOUNT="invoicex-api@invoicex-demo.iam.gserviceaccount.com",
        )
