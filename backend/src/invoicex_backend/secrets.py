"""Two-stage settings bootstrap: optional GCP Secret Manager overlay, then .env fallback."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from invoicex_backend.config import BackendSettings

logger = logging.getLogger(__name__)

# Env var name -> Secret Manager secret id (kebab-case). Wallet addresses are public
# and intentionally excluded.
MANAGED_SECRET_KEYS: dict[str, str] = {
    # Retained only for local backwards compatibility. Cloud Run's production
    # deployment deliberately does not bind this secret and uses Vertex ADC.
    "GEMINI_API_KEY": "gemini-api-key",
    "PRIVY_APP_ID": "privy-app-id",
    "PRIVY_APP_SECRET": "privy-app-secret",
    "PRIVY_WALLET_ID": "privy-wallet-id",
    "PRIVY_RWA_ISSUER_WALLET_ID": "privy-rwa-issuer-wallet-id",
    "PRIVY_SETTLEMENT_WALLET_ID": "privy-settlement-wallet-id",
    "PRIVY_SPONSOR_WALLET_ID": "privy-sponsor-wallet-id",
    "SOLANA_RPC_URL": "solana-rpc-url",
    "CLOUD_SQL_PASSWORD": "cloud-sql-password",
    "AUTH_TOKEN_SECRET": "auth-token-secret",
}

# These secrets support the separate mock repayment-distribution flow.  The
# production Cloud Run configuration intentionally disables that flow because
# the current product path is investor deposit -> agent vault -> supplier
# payout.  Avoid querying a secret that is neither provisioned nor needed.
MOCK_SETTLEMENT_SECRET_KEYS = frozenset({"PRIVY_SETTLEMENT_WALLET_ID"})


class _SecretManagerBootstrapSettings(BaseSettings):
    """Minimal settings needed to decide whether Secret Manager should be consulted.

    This has to be resolved before BackendSettings() can be constructed, because
    whether Secret Manager is enabled is itself something that may only live in .env,
    and BackendSettings() can fail validation before that value is known.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    secret_manager_enabled: bool = Field(
        default=False,
        validation_alias="SECRET_MANAGER_ENABLED",
    )
    gcp_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT"),
    )
    secret_name_prefix: str = Field(default="", validation_alias="SECRET_NAME_PREFIX")
    mock_settlement_enabled: bool = Field(
        default=True,
        validation_alias="MOCK_SETTLEMENT_ENABLED",
    )


def _create_secret_manager_client() -> Any:
    """Lazily import and construct the Secret Manager client (kept swappable for tests)."""

    from google.cloud import secretmanager

    return secretmanager.SecretManagerServiceClient()


def _fetch_secret(client: Any, project_id: str, secret_id: str) -> str:
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("utf-8")


def _apply_secret_manager_overrides(
    bootstrap: _SecretManagerBootstrapSettings,
    project_id: str,
    client_factory: Callable[[], Any],
) -> None:
    client: Any | None = None
    for env_key, secret_suffix in MANAGED_SECRET_KEYS.items():
        if (
            env_key in MOCK_SETTLEMENT_SECRET_KEYS
            and not bootstrap.mock_settlement_enabled
        ):
            continue
        if env_key in os.environ:
            continue
        try:
            if client is None:
                client = client_factory()
            secret_id = f"{bootstrap.secret_name_prefix}{secret_suffix}"
            value = _fetch_secret(client, project_id, secret_id)
        except Exception:
            logger.warning(
                "Secret Manager lookup failed for %s; falling back to .env",
                env_key,
                exc_info=True,
            )
            continue
        os.environ[env_key] = value
        logger.info("Loaded %s from Secret Manager", env_key)


def load_settings(client_factory: Callable[[], Any] | None = None) -> BackendSettings:
    """Resolve BackendSettings, optionally overlaying values from GCP Secret Manager.

    Priority: real environment variables > Secret Manager > .env file. Secret Manager
    is only consulted when SECRET_MANAGER_ENABLED is true and a GCP project id is
    configured; any Secret Manager failure is logged and silently falls back to .env.
    """

    bootstrap = _SecretManagerBootstrapSettings()
    if bootstrap.secret_manager_enabled and bootstrap.gcp_project_id:
        _apply_secret_manager_overrides(
            bootstrap,
            bootstrap.gcp_project_id,
            client_factory or _create_secret_manager_client,
        )
    return BackendSettings()
