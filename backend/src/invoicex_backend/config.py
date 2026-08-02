"""Environment-backed backend configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Runtime configuration with explicit real/mock integration modes."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
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

    firebase_mode: Literal["auto", "firebase", "local"] = Field(
        default="auto",
        validation_alias="FIREBASE_MODE",
    )
    firebase_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FIREBASE_PROJECT_ID",
            "GOOGLE_CLOUD_PROJECT",
            "GCLOUD_PROJECT",
        ),
    )
    firebase_storage_bucket: str | None = Field(
        default=None,
        validation_alias="FIREBASE_STORAGE_BUCKET",
    )
    firebase_firestore_database: str = Field(
        default="(default)",
        validation_alias="FIREBASE_FIRESTORE_DATABASE",
        min_length=1,
    )
    firebase_collection_prefix: str = Field(
        default="invoicex",
        validation_alias="FIREBASE_COLLECTION_PREFIX",
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    firebase_app_name: str = Field(
        default="invoicex-backend",
        validation_alias="FIREBASE_APP_NAME",
        min_length=1,
    )

    agent_mode: Literal["auto", "real", "mock"] = Field(
        default="auto",
        validation_alias="AGENT_MODE",
    )
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
    )
    gemini_model: str = Field(
        default="gemini-3.6-flash",
        validation_alias="GEMINI_MODEL",
    )

    solana_mode: Literal["auto", "privy", "mock"] = Field(
        default="auto",
        validation_alias="SOLANA_MODE",
    )
    privy_app_id: str | None = Field(default=None, validation_alias="PRIVY_APP_ID")
    privy_app_secret: str | None = Field(
        default=None,
        validation_alias="PRIVY_APP_SECRET",
    )
    privy_treasury_wallet_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PRIVY_TREASURY_WALLET_ID", "PRIVY_WALLET_ID"),
    )
    privy_settlement_wallet_id: str | None = Field(
        default=None,
        validation_alias="PRIVY_SETTLEMENT_WALLET_ID",
    )
    privy_rwa_wallet_id: str | None = Field(
        default=None,
        validation_alias="PRIVY_RWA_WALLET_ID",
    )
    privy_sponsor_wallet_id: str | None = Field(
        default=None,
        validation_alias="PRIVY_SPONSOR_WALLET_ID",
    )
    privy_sponsor: bool = Field(default=True, validation_alias="PRIVY_SPONSOR")
    privy_api_base_url: str = Field(
        default="https://api.privy.io",
        validation_alias="PRIVY_API_BASE_URL",
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
        gt=0,
    )

    supplier_wallet_address: str = Field(
        default="DEMO_SUPPLIER_WALLET",
        validation_alias="SUPPLIER_WALLET_ADDRESS",
    )
    investor_settlement_wallet_address: str = Field(
        default="DEMO_AGENT_VAULT",
        validation_alias="INVESTOR_SETTLEMENT_WALLET_ADDRESS",
    )
    platform_fee_wallet_address: str = Field(
        default="DEMO_PLATFORM_FEE_WALLET",
        validation_alias="PLATFORM_FEE_WALLET_ADDRESS",
    )
    mandate_min_risk_score: int = Field(
        default=80,
        validation_alias="MANDATE_MIN_RISK_SCORE",
        ge=0,
        le=100,
    )
    mandate_max_advance_usdc: int = Field(
        default=25_000,
        validation_alias="MANDATE_MAX_ADVANCE_USDC",
        gt=0,
    )

    @model_validator(mode="after")
    def validate_explicit_real_modes(self) -> BackendSettings:
        if self.firebase_mode == "firebase":
            missing = self.missing_firebase_configuration()
            if missing:
                raise ValueError(
                    "FIREBASE_MODE=firebase requires configuration: "
                    + ", ".join(missing)
                )
        if self.agent_mode == "real" and not self._non_blank(self.gemini_api_key):
            raise ValueError("AGENT_MODE=real requires GEMINI_API_KEY")
        if self.solana_mode == "privy":
            missing = self.missing_privy_funding_configuration()
            if missing:
                raise ValueError(
                    "SOLANA_MODE=privy requires configuration: " + ", ".join(missing)
                )
        return self

    def resolved_firebase_mode(self) -> Literal["firebase", "local"]:
        if self.firebase_mode == "auto":
            return (
                "firebase"
                if self._non_blank(self.firebase_project_id)
                else "local"
            )
        return self.firebase_mode

    def resolved_firebase_storage_bucket(self) -> str:
        if self._non_blank(self.firebase_storage_bucket):
            return str(self.firebase_storage_bucket).strip()
        if self._non_blank(self.firebase_project_id):
            return f"{str(self.firebase_project_id).strip()}.firebasestorage.app"
        raise ValueError("FIREBASE_PROJECT_ID is required to derive the storage bucket")

    def missing_firebase_configuration(self) -> list[str]:
        return (
            []
            if self._non_blank(self.firebase_project_id)
            else ["FIREBASE_PROJECT_ID"]
        )

    def resolved_agent_mode(self) -> Literal["real", "mock"]:
        if self.agent_mode == "auto":
            return "real" if self._non_blank(self.gemini_api_key) else "mock"
        return self.agent_mode

    def resolved_solana_mode(self) -> Literal["privy", "mock"]:
        if self.solana_mode == "auto":
            return (
                "privy"
                if not self.missing_privy_funding_configuration()
                else "mock"
            )
        return self.solana_mode

    def missing_privy_funding_configuration(self) -> list[str]:
        values = {
            "PRIVY_APP_ID": self.privy_app_id,
            "PRIVY_APP_SECRET": self.privy_app_secret,
            "PRIVY_WALLET_ID": self.privy_treasury_wallet_id,
        }
        return self._missing_configuration(values)

    def missing_privy_settlement_configuration(self) -> list[str]:
        values = {
            "PRIVY_SETTLEMENT_WALLET_ID": self.privy_settlement_wallet_id,
            "INVESTOR_SETTLEMENT_WALLET_ADDRESS": (
                self.investor_settlement_wallet_address
            ),
            "PLATFORM_FEE_WALLET_ADDRESS": self.platform_fee_wallet_address,
        }
        return self._missing_configuration(values)

    def missing_privy_rwa_configuration(self) -> list[str]:
        values = {
            "PRIVY_RWA_WALLET_ID": self.privy_rwa_wallet_id,
            "PRIVY_SPONSOR_WALLET_ID": self.privy_sponsor_wallet_id,
        }
        return self._missing_configuration(values)

    def missing_privy_configuration(self) -> list[str]:
        return [
            *self.missing_privy_funding_configuration(),
            *self.missing_privy_settlement_configuration(),
        ]

    def _missing_configuration(self, values: dict[str, str | None]) -> list[str]:
        return [
            name
            for name, value in values.items()
            if not self._non_blank(value) or str(value).startswith("DEMO_")
        ]

    @staticmethod
    def _non_blank(value: str | None) -> bool:
        return value is not None and bool(value.strip())
