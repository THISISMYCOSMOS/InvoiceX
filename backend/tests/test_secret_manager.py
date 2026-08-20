from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

from invoicex_backend.config import BackendSettings
from invoicex_backend.secrets import MANAGED_SECRET_KEYS, load_settings


class _FakeSecretManagerClient:
    """Stand-in for google.cloud.secretmanager.SecretManagerServiceClient."""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def access_secret_version(self, name: str) -> SimpleNamespace:
        secret_id = name.split("/secrets/")[1].split("/versions/")[0]
        value = self._values[secret_id]
        return SimpleNamespace(payload=SimpleNamespace(data=value.encode("utf-8")))


class _RaisingSecretManagerClient:
    def access_secret_version(self, name: str) -> Any:
        raise RuntimeError("simulated Secret Manager failure")


def _pin_non_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix the settings fields that gate validation so the real root .env can't
    leak an unexpected value into these tests (e.g. AGENT_MODE=real)."""

    monkeypatch.setenv("AGENT_MODE", "mock")
    monkeypatch.setenv("SOLANA_MODE", "mock")
    monkeypatch.setenv("GASLESS_ENABLED", "false")
    monkeypatch.setenv("MOCK_SETTLEMENT_ENABLED", "false")


def _clear_managed_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_key in MANAGED_SECRET_KEYS:
        monkeypatch.delenv(env_key, raising=False)


def test_disabled_secret_manager_never_creates_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_non_secret_env(monkeypatch)
    monkeypatch.setenv("SECRET_MANAGER_ENABLED", "false")
    monkeypatch.setenv("GCP_PROJECT_ID", "demo-project")

    created = False

    def factory() -> Any:
        nonlocal created
        created = True
        raise AssertionError("client factory must not be called when disabled")

    settings = load_settings(client_factory=factory)

    assert created is False
    assert settings.resolved_agent_mode() == "mock"


def test_enabled_injects_missing_keys_from_secret_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_non_secret_env(monkeypatch)
    _clear_managed_keys(monkeypatch)
    monkeypatch.setenv("SECRET_MANAGER_ENABLED", "true")
    monkeypatch.setenv("GCP_PROJECT_ID", "demo-project")
    monkeypatch.setenv("SECRET_NAME_PREFIX", "")

    fake_client = _FakeSecretManagerClient(
        {
            "solana-rpc-url": "https://sm.example.com/rpc",
            "privy-app-id": "sm-privy-app-id",
            "privy-app-secret": "sm-privy-app-secret",
            "privy-wallet-id": "sm-privy-wallet-id",
            "privy-rwa-issuer-wallet-id": "sm-privy-issuer-id",
            "privy-settlement-wallet-id": "sm-privy-settlement-id",
            "privy-sponsor-wallet-id": "sm-privy-sponsor-id",
        }
    )

    settings = load_settings(client_factory=lambda: fake_client)

    assert settings.solana_rpc_url == "https://sm.example.com/rpc"
    assert settings.privy_app_id == "sm-privy-app-id"
    assert settings.privy_settlement_wallet_id == "sm-privy-settlement-id"


def test_enabled_does_not_overwrite_existing_env_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_non_secret_env(monkeypatch)
    _clear_managed_keys(monkeypatch)
    monkeypatch.setenv("SECRET_MANAGER_ENABLED", "true")
    monkeypatch.setenv("GCP_PROJECT_ID", "demo-project")
    monkeypatch.setenv("SECRET_NAME_PREFIX", "")
    monkeypatch.setenv("PRIVY_APP_ID", "env-value-must-survive")

    fake_client = _FakeSecretManagerClient({"privy-app-id": "sm-value-should-be-ignored"})

    settings = load_settings(client_factory=lambda: fake_client)

    assert settings.privy_app_id == "env-value-must-survive"


def test_secret_manager_failure_falls_back_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_non_secret_env(monkeypatch)
    _clear_managed_keys(monkeypatch)
    monkeypatch.setenv("SECRET_MANAGER_ENABLED", "true")
    monkeypatch.setenv("GCP_PROJECT_ID", "demo-project")
    monkeypatch.setenv("SECRET_NAME_PREFIX", "")

    settings = load_settings(client_factory=lambda: _RaisingSecretManagerClient())

    # No exception propagated, and the failing client must not have injected
    # anything into the process environment (fallback to .env/defaults happens
    # naturally inside BackendSettings without this test asserting on real
    # root .env contents).
    assert isinstance(settings, BackendSettings)
    assert "SOLANA_RPC_URL" not in os.environ
