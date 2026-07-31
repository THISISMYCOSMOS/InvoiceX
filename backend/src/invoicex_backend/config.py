"""Environment-backed backend configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/invoicex_backend/config.py -> backend/seed
DEFAULT_SEED_DIRECTORY = Path(__file__).resolve().parents[2] / "seed"


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
    state_file: Path | None = Field(
        default=None,
        validation_alias="STATE_FILE",
    )
    seed_directory: Path | None = Field(
        default=None,
        validation_alias="SEED_DIRECTORY",
    )

    @field_validator("state_file", "seed_directory", mode="before")
    @classmethod
    def blank_path_means_unset(cls, value: object) -> object:
        """A blank `STATE_FILE=`/`SEED_DIRECTORY=` must not resolve to Path('.')."""

        if isinstance(value, str) and not value.strip():
            return None
        return value
    max_document_size_bytes: int = Field(
        default=20 * 1024 * 1024,
        validation_alias="MAX_DOCUMENT_SIZE_BYTES",
        ge=1,
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
        if self.agent_mode == "real" and not self._non_blank(self.gemini_api_key):
            raise ValueError("AGENT_MODE=real requires GEMINI_API_KEY")
        if self.solana_mode == "privy":
            missing = self.missing_privy_configuration()
            if missing:
                raise ValueError(
                    "SOLANA_MODE=privy requires configuration: " + ", ".join(missing)
                )
        return self

    def resolved_state_file(self) -> Path:
        """Default the snapshot next to the uploads so each deployment stays isolated."""

        if self.state_file is not None:
            return self.state_file
        return self.upload_directory.parent / "state.json"

    def resolved_seed_directory(self) -> Path:
        """Resolve the demo seed relative to the package, not the working directory."""

        if self.seed_directory is not None:
            return self.seed_directory
        return DEFAULT_SEED_DIRECTORY

    def resolved_agent_mode(self) -> Literal["real", "mock"]:
        if self.agent_mode == "auto":
            return "real" if self._non_blank(self.gemini_api_key) else "mock"
        return self.agent_mode

    def resolved_solana_mode(self) -> Literal["privy", "mock"]:
        if self.solana_mode == "auto":
            return "privy" if not self.missing_privy_configuration() else "mock"
        return self.solana_mode

    def missing_privy_configuration(self) -> list[str]:
        values = {
            "PRIVY_APP_ID": self.privy_app_id,
            "PRIVY_APP_SECRET": self.privy_app_secret,
            "PRIVY_WALLET_ID": self.privy_treasury_wallet_id,
            "PRIVY_SETTLEMENT_WALLET_ID": self.privy_settlement_wallet_id,
            "SUPPLIER_WALLET_ADDRESS": self.supplier_wallet_address,
            "INVESTOR_SETTLEMENT_WALLET_ADDRESS": (
                self.investor_settlement_wallet_address
            ),
            "PLATFORM_FEE_WALLET_ADDRESS": self.platform_fee_wallet_address,
        }
        return [
            name
            for name, value in values.items()
            if not self._non_blank(value) or str(value).startswith("DEMO_")
        ]

    @staticmethod
    def _non_blank(value: str | None) -> bool:
        return value is not None and bool(value.strip())
