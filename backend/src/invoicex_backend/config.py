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
    gemini_timeout_seconds: float = Field(
        default=60,
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
    gasless_deposit_max_usdc: int = Field(
        default=1,
        validation_alias="GASLESS_DEPOSIT_MAX_USDC",
        gt=0,
    )
    privy_api_base_url: str = Field(
        default="https://api.privy.io",
        validation_alias="PRIVY_API_BASE_URL",
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
        if self.agent_mode == "real" and not self._non_blank(self.gemini_api_key):
            raise ValueError("AGENT_MODE=real requires GEMINI_API_KEY")
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

    def resolved_agent_mode(self) -> Literal["real", "mock"]:
        if self.agent_mode == "auto":
            return "real" if self._non_blank(self.gemini_api_key) else "mock"
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
        return [
            name
            for name, value in values.items()
            if not self._non_blank(value) or str(value).startswith("DEMO_")
        ]

    def missing_gasless_configuration(self) -> list[str]:
        values = {
            "PRIVY_SPONSOR_WALLET_ID": self.privy_sponsor_wallet_id,
            "PRIVY_SPONSOR_WALLET_ADDRESS": self.privy_sponsor_wallet_address,
        }
        return [name for name, value in values.items() if not self._non_blank(value)]

    @staticmethod
    def _non_blank(value: str | None) -> bool:
        return value is not None and bool(value.strip())
