from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from invoicex_backend.config import BackendSettings


def mock_settings(upload_directory: Path, **overrides: object) -> BackendSettings:
    values: dict[str, object] = {
        "AGENT_MODE": "mock",
        "SOLANA_MODE": "mock",
        "UPLOAD_DIRECTORY": upload_directory,
        "RWA_DATABASE_PATH": upload_directory.parent / "invoicex-rwa.sqlite3",
        "PUBLIC_BASE_URL": "http://testserver",
        "MVP_SOFR_BPS": 362,
        "SOFR_AS_OF": "2026-08-14",
        "SOFR_SOURCE": "Federal Reserve Bank of New York",
    }
    values.update(overrides)
    return BackendSettings(_env_file=None, **values)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(settings=mock_settings(tmp_path / "uploads"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def contract_files() -> dict[str, tuple[str, bytes, str]]:
    pdf = b"%PDF-1.4\nInvoiceX deterministic test document\n%%EOF"
    return {
        "INVOICE": ("invoice.pdf", pdf, "application/pdf"),
        "CONTRACT": ("contract.pdf", pdf, "application/pdf"),
        "PURCHASE_ORDER": ("purchase-order.pdf", pdf, "application/pdf"),
        "DELIVERY_PROOF": ("delivery-proof.png", b"\x89PNG\r\n\x1a\n", "image/png"),
    }
