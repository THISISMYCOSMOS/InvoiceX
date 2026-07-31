"""State must survive a process restart for the demo to be resumable."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invoicex_backend.agents import MockAgentGateway
from invoicex_backend.app import create_app
from invoicex_backend.config import BackendSettings
from invoicex_backend.models import DocumentType, UploadedDocument
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import create_solana_gateway
from invoicex_backend.state_store import (
    STATE_SCHEMA_VERSION,
    JsonStateStore,
    PersistedState,
)
from invoicex_backend.storage import LocalDocumentStorage
from tests.conftest import deterministic_pdf, mock_settings


def restarted_client(settings: BackendSettings) -> TestClient:
    """Build a brand new app against the same settings, as a restart would."""

    return TestClient(create_app(settings=settings))


def test_invoice_state_survives_restart(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")

    with restarted_client(settings) as client:
        created = client.post("/api/v1/invoices", files=contract_files).json()
        invoice_id = created["invoice"]["id"]
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]

    assert settings.resolved_state_file().exists()

    with restarted_client(settings) as client:
        recovered = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert recovered["status"] == "BUYER_REVIEW"
        assert recovered["verificationId"] == verification_id
        assert len(recovered["documents"]) == 4
        assert recovered["analysis"]["amountKrw"]["value"] == 20_000_000
        assert client.get("/api/v1/verifications").json()["items"][0][
            "id"
        ] == verification_id

        # The restored agent analysis must still drive the Risk Passport.
        offered = client.post(
            f"/api/v1/verifications/{verification_id}/confirm"
        ).json()["invoice"]
        assert offered["status"] == "OFFER_READY"
        assert offered["riskPassport"]["suggestedAdvanceAmountUsdc"] == 18_800


def test_restart_does_not_reuse_identifiers(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")

    with restarted_client(settings) as client:
        first = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]

    with restarted_client(settings) as client:
        second = client.post("/api/v1/invoices", files=contract_files).json()["invoice"]
        assert second["id"] != first["id"]
        assert {item["id"] for item in client.get("/api/v1/invoices").json()["items"]} == {
            first["id"],
            second["id"],
        }
        document_ids = [document["id"] for document in second["documents"]]
        assert len(set(document_ids)) == 4
        assert not set(document_ids) & {
            document["id"] for document in first["documents"]
        }


def test_settled_invoice_is_still_settled_after_restart(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")

    with restarted_client(settings) as client:
        invoice_id = client.post("/api/v1/invoices", files=contract_files).json()[
            "invoice"
        ]["id"]
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")
        client.post(
            f"/api/v1/invoices/{invoice_id}/offer-response",
            json={"response": "ACCEPT"},
        )
        settled = client.post(
            f"/api/v1/invoices/{invoice_id}/settlement/mock-payment"
        ).json()["invoice"]
        signature = settled["settlementTransaction"]["signature"]

    with restarted_client(settings) as client:
        recovered = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
        assert recovered["status"] == "SETTLED"
        assert recovered["settlementTransaction"]["signature"] == signature
        assert recovered["fundingTransaction"]["amountUsdc"] == 18_800
        assert recovered["settlement"]["investorSettlementUsdc"] == 19_800
        assert client.get("/api/v1/investor/dashboard").json()[
            "outstandingPrincipalUsdc"
        ] == 0
        # A settled invoice must stay idempotent across the restart too.
        again = client.post(
            f"/api/v1/invoices/{invoice_id}/settlement/mock-payment"
        ).json()["invoice"]
        assert again["settlementTransaction"]["signature"] == signature


def test_unreadable_state_is_quarantined_not_deleted(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{ this is not json", encoding="utf-8")
    store = JsonStateStore(path)

    state = store.load()

    assert state.invoices == {}
    assert path.with_name("state.json.corrupt").exists()
    assert not path.exists()


def test_unknown_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps({"schema_version": STATE_SCHEMA_VERSION + 1, "invoices": {}}),
        encoding="utf-8",
    )
    store = JsonStateStore(path)

    assert store.load().invoices == {}
    assert path.with_name("state.json.corrupt").exists()


def test_blank_state_file_env_does_not_target_the_working_directory() -> None:
    """`STATE_FILE=` must fall back to the default, not to Path('.')."""

    settings = BackendSettings(_env_file=None, STATE_FILE="", UPLOAD_DIRECTORY="uploads")

    assert settings.state_file is None
    assert settings.resolved_state_file() == Path("state.json")


def test_directory_is_rejected_as_a_state_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="디렉터리"):
        JsonStateStore(tmp_path)

    assert tmp_path.is_dir()
    assert not tmp_path.with_name(f"{tmp_path.name}.corrupt").exists()


def test_save_leaves_no_temporary_file_and_is_atomic(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "state.json"
    store = JsonStateStore(path)

    store.save(PersistedState(invoice_sequence=7))

    assert store.load().invoice_sequence == 7
    assert list(path.parent.iterdir()) == [path]


def test_save_failure_keeps_serving_from_memory(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path / "state.json")
    store.save(PersistedState(invoice_sequence=1))
    # Replacing the file with a directory makes os.replace fail.
    store.path.unlink()
    store.path.mkdir()

    store.save(PersistedState(invoice_sequence=2))

    assert not (tmp_path / "state.json.tmp").exists()


class SlowFirstSaveStore(JsonStateStore):
    """Delay only the first write so a stale snapshot would land last."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.saves = 0

    def save(self, state: PersistedState) -> None:
        self.saves += 1
        if self.saves == 1:
            time.sleep(0.2)
        super().save(state)


def test_a_slow_writer_cannot_overwrite_a_newer_snapshot(tmp_path: Path) -> None:
    """The persist lock must serialize snapshot building with its own write.

    Without it, a writer that built its snapshot first but finished last would
    replace newer state on disk with its stale copy.
    """

    settings = mock_settings(tmp_path / "uploads")
    store = SlowFirstSaveStore(settings.resolved_state_file())
    service = InvoiceService(
        settings=settings,
        agent_gateway=MockAgentGateway(),
        solana_gateway=create_solana_gateway(settings),
        storage=LocalDocumentStorage(settings),
        state_store=store,
    )

    async def interleave() -> None:
        service._invoice_sequence = 1
        slow = asyncio.create_task(service._persist())
        await asyncio.sleep(0.05)
        service._invoice_sequence = 2
        await service._persist()
        await slow

    asyncio.run(interleave())

    assert store.saves == 2
    assert store.load().invoice_sequence == 2


def test_concurrent_creates_persist_every_invoice(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    """Two invoices created at once must both reach the snapshot."""

    settings = mock_settings(tmp_path / "uploads")
    app = create_app(settings=settings)
    service = app.state.invoice_service
    uploads = [
        UploadedDocument(
            type=document_type,
            file_name=f"{document_type.value.lower()}.pdf",
            mime_type="application/pdf",
            data=deterministic_pdf(),
        )
        for document_type in DocumentType
    ]

    async def create_both() -> list[str]:
        created = await asyncio.gather(
            service.create_invoice(list(uploads)),
            service.create_invoice(list(uploads)),
        )
        return [invoice.id for invoice in created]

    invoice_ids = asyncio.run(create_both())
    assert len(set(invoice_ids)) == 2

    persisted = PersistedState.model_validate_json(
        settings.resolved_state_file().read_bytes()
    )
    assert set(persisted.invoices) == set(invoice_ids)
    assert set(persisted.agent_analyses) == set(invoice_ids)
    assert persisted.invoice_sequence == 2
    assert persisted.document_sequence == 8
