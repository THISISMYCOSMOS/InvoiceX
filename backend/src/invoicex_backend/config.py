"""Environment-backed backend configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Runtime configuration with explicit real/mock integration modes."""

    model_config = SettingsConfigDict(
        # Backend development uses Vertex AI configuration from backend/.env;
        # it never imports legacy Agent API-key settings.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    port: int = Field(default=8000, validation_alias="PORT", ge=1, le=65535)
    public_base_url: str = Field(
        default="http://localhost:8000",
        validation_alias="PUBLIC_BASE_URL",
    )
    frontend_origin: str = Field(
        default="http://localhost:5173",
        validation_alias="FRONTEND_ORIGIN",
    )
    upload_directory: Path = Field(
        default=Path("uploads"),
        validation_alias="UPLOAD_DIRECTORY",
    )
    max_document_size_bytes: int = Field(
        default=20 * 1024 * 1024,
        validation_alias="MAX_DOCUMENT_SIZE_BYTES",
        ge=1,
    )
    deployment_target: Literal["local", "gcp"] = Field(
        default="local",
        validation_alias="DEPLOYMENT_TARGET",
    )
    persistence_backend: Literal["sqlite", "cloud_sql"] = Field(
        default="sqlite",
        validation_alias="PERSISTENCE_BACKEND",
    )
    document_storage_backend: Literal["local", "gcs"] = Field(
        default="local",
        validation_alias="DOCUMENT_STORAGE_BACKEND",
    )
    gcp_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT"),
    )
    cloud_sql_instance_connection_name: str | None = Field(
        default=None,
        validation_alias="CLOUD_SQL_INSTANCE_CONNECTION_NAME",
    )
    cloud_sql_database: str | None = Field(
        default=None,
        validation_alias="CLOUD_SQL_DATABASE",
    )
    cloud_sql_user: str | None = Field(
        default=None,
        validation_alias="CLOUD_SQL_USER",
    )
    cloud_sql_password: str | None = Field(
        default=None,
        validation_alias="CLOUD_SQL_PASSWORD",
    )
    cloud_sql_ip_type: Literal["public", "private"] = Field(
        default="public",
        validation_alias="CLOUD_SQL_IP_TYPE",
    )
    gcs_document_bucket: str | None = Field(
        default=None,
        validation_alias="GCS_DOCUMENT_BUCKET",
    )
    gcs_document_prefix: str = Field(
        default="invoices",
        validation_alias="GCS_DOCUMENT_PREFIX",
    )
    gcs_signed_url_ttl_seconds: int = Field(
        default=900,
        validation_alias="GCS_SIGNED_URL_TTL_SECONDS",
        ge=60,
        le=3600,
    )
    gcs_signing_service_account: str | None = Field(
        default=None,
        validation_alias="GCS_SIGNING_SERVICE_ACCOUNT",
    )
    api_auth_required: bool = Field(default=False, validation_alias="API_AUTH_REQUIRED")
    auth_token_secret: str = Field(
        default="local-development-only-token-secret",
        validation_alias="AUTH_TOKEN_SECRET",
        min_length=32,
    )
    auth_token_ttl_seconds: int = Field(
        default=60 * 60 * 8,
        validation_alias="AUTH_TOKEN_TTL_SECONDS",
        ge=300,
        le=60 * 60 * 24,
    )

    agent_mode: Literal["auto", "real", "mock"] = Field(
        default="auto",
        validation_alias="AGENT_MODE",
    )
    vertex_ai_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VERTEX_AI_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "GCP_PROJECT_ID"),
    )
    vertex_ai_location: str = Field(
        default="global",
        validation_alias="VERTEX_AI_LOCATION",
        min_length=1,
    )
    risk_scoring_provider: Literal["deterministic"] = Field(
        default="deterministic",
        validation_alias="RISK_SCORING_PROVIDER",
    )
    mvp_sofr_rate: float = Field(
        default=0.05,
        validation_alias="MVP_SOFR_RATE",
        ge=0,
        le=1,
        description="Annual SOFR decimal fraction used by the MVP pricing policy.",
    )
    risk_spread_90: float = Field(default=0.015, validation_alias="RISK_SPREAD_90", ge=0, le=1)
    risk_spread_80: float = Field(default=0.025, validation_alias="RISK_SPREAD_80", ge=0, le=1)
    risk_spread_70: float = Field(default=0.04, validation_alias="RISK_SPREAD_70", ge=0, le=1)
    country_spread_low: float = Field(default=0.005, validation_alias="COUNTRY_SPREAD_LOW", ge=0, le=1)
    country_spread_medium: float = Field(default=0.015, validation_alias="COUNTRY_SPREAD_MEDIUM", ge=0, le=1)
    country_spread_high: float = Field(default=0.03, validation_alias="COUNTRY_SPREAD_HIGH", ge=0, le=1)
    platform_fee_rate: float = Field(default=0.012, validation_alias="PLATFORM_FEE_RATE", ge=0, le=1)
    agent_task_dispatcher: Literal["inline", "cloud_tasks"] = Field(
        default="inline",
        validation_alias="AGENT_TASK_DISPATCHER",
    )
    cloud_tasks_queue: str | None = Field(default=None, validation_alias="CLOUD_TASKS_QUEUE")
    cloud_tasks_location: str | None = Field(default=None, validation_alias="CLOUD_TASKS_LOCATION")
    cloud_run_task_audience: str | None = Field(default=None, validation_alias="CLOUD_RUN_TASK_AUDIENCE")
    cloud_tasks_service_account_email: str | None = Field(
        default=None, validation_alias="CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL"
    )
    gemini_model: str = Field(
        default="gemini-3.6-flash",
        validation_alias="GEMINI_MODEL",
    )
    gemini_timeout_seconds: float = Field(
        default=180,
        validation_alias="GEMINI_TIMEOUT_SECONDS",
        gt=0,
        le=300,
    )
    gemini_max_attempts: int = Field(
        default=2,
        validation_alias="GEMINI_MAX_ATTEMPTS",
        ge=1,
        le=3,
    )

    solana_mode: Literal["auto", "direct", "privy", "mock"] = Field(
        default="auto",
        validation_alias="SOLANA_MODE",
    )
    privy_app_id: str | None = Field(default=None, validation_alias="PRIVY_APP_ID")
    privy_app_secret: str | None = Field(
        default=None,
        validation_alias="PRIVY_APP_SECRET",
    )
    privy_verification_key: str | None = Field(
        default=None,
        validation_alias="PRIVY_VERIFICATION_KEY",
    )
    privy_jwks_url: str | None = Field(
        default=None,
        validation_alias="PRIVY_JWKS_URL",
    )
    privy_treasury_wallet_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PRIVY_TREASURY_WALLET_ID", "PRIVY_WALLET_ID"),
    )
    privy_rwa_issuer_wallet_id: str | None = Field(
        default=None,
        validation_alias="PRIVY_RWA_ISSUER_WALLET_ID",
    )
    privy_settlement_wallet_id: str | None = Field(
        default=None,
        validation_alias="PRIVY_SETTLEMENT_WALLET_ID",
    )
    # This controls Privy's managed gas-sponsorship product, not the separate
    # Privy Sponsor wallet used by InvoiceX as the actual Solana fee payer.
    # Keep it opt-in: our dedicated Sponsor wallet does not require the Privy
    # product to be enabled.
    privy_sponsor: bool = Field(default=False, validation_alias="PRIVY_SPONSOR")
    gasless_enabled: bool = Field(default=False, validation_alias="GASLESS_ENABLED")
    privy_sponsor_wallet_id: str | None = Field(
        default=None,
        validation_alias="PRIVY_SPONSOR_WALLET_ID",
    )
    privy_sponsor_wallet_address: str | None = Field(
        default=None,
        validation_alias="PRIVY_SPONSOR_WALLET_ADDRESS",
    )
    mock_settlement_enabled: bool = Field(
        default=True,
        validation_alias="MOCK_SETTLEMENT_ENABLED",
    )
    privy_api_base_url: str = Field(
        default="https://api.privy.io",
        validation_alias="PRIVY_API_BASE_URL",
    )
    privy_api_timeout_seconds: float = Field(
        default=15,
        validation_alias="PRIVY_API_TIMEOUT_SECONDS",
        gt=0,
        le=60,
    )
    privy_otp_display_ttl_seconds: int = Field(
        default=300,
        validation_alias="PRIVY_OTP_DISPLAY_TTL_SECONDS",
        ge=30,
        le=3600,
    )
    # Privy's transaction broadcaster may be separate from the configured RPC.
    # The rpc option keeps a Devnet transaction's recent blockhash and broadcast
    # on the same RPC while Privy still holds every service-wallet private key.
    privy_broadcast_mode: Literal["privy", "rpc"] = Field(
        default="privy",
        validation_alias="PRIVY_BROADCAST_MODE",
    )

    solana_cluster: Literal["devnet"] = Field(
        default="devnet",
        validation_alias="SOLANA_CLUSTER",
    )
    solana_rpc_url: str = Field(
        default="https://api.devnet.solana.com",
        validation_alias="SOLANA_RPC_URL",
    )
    solana_caip2: str = Field(
        default="solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1",
        validation_alias="SOLANA_CAIP2",
    )
    solana_usdc_mint: str = Field(
        default="4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
        validation_alias="SOLANA_USDC_MINT",
    )
    solana_usdc_decimals: int = Field(
        default=6,
        validation_alias="SOLANA_USDC_DECIMALS",
        ge=0,
        le=18,
    )
    solana_confirmation_timeout_seconds: float = Field(
        default=30,
        validation_alias="SOLANA_CONFIRMATION_TIMEOUT_SECONDS",
        gt=0,
        le=120,
    )
    solana_demo_transfer_amount_usdc: int = Field(
        default=1,
        validation_alias="SOLANA_DEMO_TRANSFER_AMOUNT_USDC",
        ge=1,
    )
    demo_krw_per_usdc: int = Field(
        default=1_000,
        validation_alias="DEMO_KRW_PER_USDC",
        ge=1,
    )
    rwa_database_path: Path = Field(
        default=Path("invoicex-devnet.sqlite3"),
        validation_alias="RWA_DATABASE_PATH",
    )
    solana_platform_keypair: str | None = Field(
        default=None,
        validation_alias="SOLANA_PLATFORM_KEYPAIR",
    )
    solana_agent_vault_keypair: str | None = Field(
        default=None,
        validation_alias="SOLANA_AGENT_VAULT_KEYPAIR",
    )
    demo_stablecoin_mint: str | None = Field(
        default=None,
        validation_alias="DEMO_STABLECOIN_MINT",
    )

    supplier_wallet_address: str = Field(
        default="DEMO_SUPPLIER_WALLET",
        validation_alias="SUPPLIER_WALLET_ADDRESS",
    )
    investor_settlement_wallet_address: str = Field(
        default="DEMO_AGENT_VAULT",
        validation_alias=AliasChoices(
            "PRIVY_TREASURY_WALLET_ADDRESS",
            "INVESTOR_SETTLEMENT_WALLET_ADDRESS",
        ),
    )
    platform_fee_wallet_address: str = Field(
        default="DEMO_PLATFORM_FEE_WALLET",
        validation_alias="PLATFORM_FEE_WALLET_ADDRESS",
    )

    @model_validator(mode="after")
    def validate_explicit_real_modes(self) -> BackendSettings:
        if (
            self.api_auth_required
            and self.auth_token_secret == "local-development-only-token-secret"
        ):
            raise ValueError(
                "API_AUTH_REQUIRED=true requires a non-default AUTH_TOKEN_SECRET "
                "from Secret Manager"
            )
        if self.deployment_target == "gcp":
            missing = {
                "GCP_PROJECT_ID": self.gcp_project_id,
                "CLOUD_SQL_INSTANCE_CONNECTION_NAME": self.cloud_sql_instance_connection_name,
                "CLOUD_SQL_DATABASE": self.cloud_sql_database,
                "CLOUD_SQL_USER": self.cloud_sql_user,
                "CLOUD_SQL_PASSWORD": self.cloud_sql_password,
                "GCS_DOCUMENT_BUCKET": self.gcs_document_bucket,
                "GCS_SIGNING_SERVICE_ACCOUNT": self.gcs_signing_service_account,
            }
            absent = [name for name, value in missing.items() if not self._non_blank(value)]
            if absent:
                raise ValueError(
                    "DEPLOYMENT_TARGET=gcp requires configuration: " + ", ".join(absent)
                )
            if self.persistence_backend != "cloud_sql":
                raise ValueError("DEPLOYMENT_TARGET=gcp requires PERSISTENCE_BACKEND=cloud_sql")
            if self.document_storage_backend != "gcs":
                raise ValueError("DEPLOYMENT_TARGET=gcp requires DOCUMENT_STORAGE_BACKEND=gcs")
            if not self.api_auth_required:
                raise ValueError("DEPLOYMENT_TARGET=gcp requires API_AUTH_REQUIRED=true")
            if self.resolved_agent_mode() == "real" and not self._non_blank(
                self.vertex_ai_project_id
            ):
                raise ValueError("real AGENT_MODE on GCP requires VERTEX_AI_PROJECT_ID")
            if self.agent_task_dispatcher == "cloud_tasks":
                task_values = {
                    "CLOUD_TASKS_QUEUE": self.cloud_tasks_queue,
                    "CLOUD_TASKS_LOCATION": self.cloud_tasks_location,
                    "CLOUD_RUN_TASK_AUDIENCE": self.cloud_run_task_audience,
                    "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL": self.cloud_tasks_service_account_email,
                }
                absent = [name for name, value in task_values.items() if not self._non_blank(value)]
                if absent:
                    raise ValueError("Cloud Tasks requires configuration: " + ", ".join(absent))
            if self.resolved_solana_mode() == "privy":
                live_settlement_values = {
                    "PRIVY_SETTLEMENT_WALLET_ID": self.privy_settlement_wallet_id,
                    "PLATFORM_FEE_WALLET_ADDRESS": self.platform_fee_wallet_address,
                }
                absent = [
                    name
                    for name, value in live_settlement_values.items()
                    if not self._non_blank(value) or str(value).startswith("DEMO_")
                ]
                if absent:
                    raise ValueError(
                        "GCP Privy settlement requires configuration: " + ", ".join(absent)
                    )
            if self.mock_settlement_enabled:
                settlement_values = {
                    "PRIVY_SETTLEMENT_WALLET_ID": self.privy_settlement_wallet_id,
                    "PLATFORM_FEE_WALLET_ADDRESS": self.platform_fee_wallet_address,
                }
                absent = [
                    name
                    for name, value in settlement_values.items()
                    if not self._non_blank(value) or str(value).startswith("DEMO_")
                ]
                if absent:
                    raise ValueError(
                        "GCP mock settlement requires configuration: " + ", ".join(absent)
                    )
        if self.agent_mode == "real" and not self._non_blank(self.vertex_ai_project_id):
            raise ValueError("AGENT_MODE=real requires VERTEX_AI_PROJECT_ID")
        if self.solana_mode == "privy":
            missing = self.missing_privy_configuration()
            if missing:
                raise ValueError("SOLANA_MODE=privy requires configuration: " + ", ".join(missing))
        if self.solana_mode == "direct":
            missing = self.missing_direct_solana_configuration()
            if missing:
                raise ValueError("SOLANA_MODE=direct requires configuration: " + ", ".join(missing))
        if self.gasless_enabled:
            if self.resolved_solana_mode() != "privy":
                raise ValueError("GASLESS_ENABLED requires a complete Privy Solana configuration")
            missing = self.missing_gasless_configuration()
            if missing:
                raise ValueError("GASLESS_ENABLED requires configuration: " + ", ".join(missing))
        return self

    def resolved_agent_mode(self) -> Literal["real", "mock", "unavailable"]:
        if self.agent_mode == "auto":
            if self._non_blank(self.vertex_ai_project_id):
                return "real"
            # Auto mode must never fabricate extraction data. Demo analysis is
            # available only when AGENT_MODE=mock is selected explicitly.
            return "unavailable"
        return self.agent_mode

    def resolved_solana_mode(self) -> Literal["direct", "privy", "mock"]:
        if self.solana_mode == "auto":
            if not self.missing_privy_configuration():
                return "privy"
            return "direct" if not self.missing_direct_solana_configuration() else "mock"
        return self.solana_mode

    def missing_direct_solana_configuration(self) -> list[str]:
        values = {
            "SOLANA_PLATFORM_KEYPAIR": self.solana_platform_keypair,
            "SOLANA_AGENT_VAULT_KEYPAIR": self.solana_agent_vault_keypair,
            "DEMO_STABLECOIN_MINT": self.demo_stablecoin_mint,
        }
        return [name for name, value in values.items() if not self._non_blank(value)]

    def missing_privy_configuration(self) -> list[str]:
        values = {
            "PRIVY_APP_ID": self.privy_app_id,
            "PRIVY_APP_SECRET": self.privy_app_secret,
            "PRIVY_WALLET_ID": self.privy_treasury_wallet_id,
            "PRIVY_RWA_ISSUER_WALLET_ID": self.privy_rwa_issuer_wallet_id,
            "INVESTOR_SETTLEMENT_WALLET_ADDRESS": (self.investor_settlement_wallet_address),
        }
        missing = [
            name
            for name, value in values.items()
            if not self._non_blank(value) or str(value).startswith("DEMO_")
        ]
        if not self._non_blank(self.privy_verification_key) and not self._non_blank(
            self.privy_jwks_url
        ):
            missing.append("PRIVY_VERIFICATION_KEY or PRIVY_JWKS_URL")
        return missing

    def missing_gasless_configuration(self) -> list[str]:
        values = {
            "PRIVY_SPONSOR_WALLET_ID": self.privy_sponsor_wallet_id,
            "PRIVY_SPONSOR_WALLET_ADDRESS": self.privy_sponsor_wallet_address,
        }
        return [name for name, value in values.items() if not self._non_blank(value)]

    @staticmethod
    def _non_blank(value: str | None) -> bool:
        return value is not None and bool(value.strip())
