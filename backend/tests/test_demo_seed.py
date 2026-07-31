"""Demo reset must rebuild a runnable scenario without re-uploading documents."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from invoicex_backend.errors import DocumentValidationError, StateConflictError
from invoicex_backend.models import DocumentType, InvoiceStatus
from invoicex_backend.seed import SEED_FILE_NAMES, load_seed_documents
from tests.conftest import mock_settings
from tests.test_async_analysis import build_service, uploads


def test_seed_directory_ships_all_four_documents() -> None:
    from invoicex_backend.config import DEFAULT_SEED_DIRECTORY

    documents = load_seed_documents(DEFAULT_SEED_DIRECTORY)

    assert {document.type for document in documents} == set(DocumentType)
    assert all(document.data.startswith(b"%PDF") for document in documents)
    assert set(SEED_FILE_NAMES.values()) == {
        path.name for path in DEFAULT_SEED_DIRECTORY.glob("*.pdf")
    }


def test_missing_seed_directory_reports_the_path(tmp_path: Path) -> None:
    with pytest.raises(DocumentValidationError, match="시드 문서를 읽을 수 없습니다"):
        load_seed_documents(tmp_path / "absent")


def test_reset_returns_a_draft_invoice_and_clears_everything(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)

    async def scenario() -> str:
        created = await service.create_invoice(uploads())
        await service.complete_document_analysis(created.id)
        await service.request_verification(created.id)
        reset = await service.reset_demo()
        return reset.id

    seeded_id = asyncio.run(scenario())

    # The mock adapter resets to a single DRAFT invoice, so the API does too.
    assert seeded_id.endswith("-001")
    seeded = service.get_invoice(seeded_id)
    assert seeded.status is InvoiceStatus.DRAFT
    assert seeded.documents == []
    assert seeded.analysis is None
    assert seeded.agent_traces == []
    assert [invoice.id for invoice in service.list_invoices()] == [seeded_id]
    assert service.list_verifications() == []

    # And the reset must outlive a restart.
    restarted = build_service(settings)
    assert [invoice.id for invoice in restarted.list_invoices()] == [seeded_id]
    assert restarted.get_invoice(seeded_id).status is InvoiceStatus.DRAFT


def test_reset_deletes_uploaded_files_but_keeps_the_directory(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)
    upload_directory = settings.upload_directory
    (upload_directory).mkdir(parents=True, exist_ok=True)
    (upload_directory / ".gitkeep").write_text("", encoding="utf-8")
    outsider = tmp_path / "keep-me.txt"
    outsider.write_text("untouched", encoding="utf-8")

    async def scenario() -> None:
        created = await service.create_invoice(uploads())
        await service.complete_document_analysis(created.id)
        assert len(list(upload_directory.glob("*.pdf"))) == 4
        await service.reset_demo()

    asyncio.run(scenario())

    assert upload_directory.is_dir()
    assert list(upload_directory.glob("*.pdf")) == []
    assert (upload_directory / ".gitkeep").exists()
    assert outsider.read_text(encoding="utf-8") == "untouched"


def test_seeded_documents_flow_through_the_real_document_agent_path(
    tmp_path: Path,
) -> None:
    """The seed must survive the agent's source-evidence validation in mock mode."""

    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)

    async def scenario() -> str:
        seeded = await service.reset_demo()
        analyzing = await service.analyze_seeded_documents(seeded.id)
        assert analyzing.status is InvoiceStatus.DOCUMENT_ANALYZING
        assert len(analyzing.documents) == 4
        await service.complete_document_analysis(seeded.id)
        return seeded.id

    invoice_id = asyncio.run(scenario())

    invoice = service.get_invoice(invoice_id)
    assert invoice.status is InvoiceStatus.DOCUMENT_REVIEW_REQUIRED
    assert invoice.analysis is not None
    # Values come from the seed PDFs, not from a hardcoded English placeholder.
    assert invoice.analysis.amount_krw.value == 20_000_000
    assert invoice.analysis.invoice_number.value == "INV-2026-0001"
    assert invoice.analysis.supplier_name.value == "(주)알파컴포넌츠"
    assert invoice.analysis.due_date.value == "2026-10-30"
    assert invoice.analysis.delivery_completed.value is True
    assert {document.type for document in invoice.documents} == set(DocumentType)


def test_seeded_invoice_reaches_an_eligible_offer(tmp_path: Path) -> None:
    """A reset demo must still produce the 18,800 USDC happy path."""

    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)

    async def scenario() -> str:
        seeded = await service.reset_demo()
        await service.analyze_seeded_documents(seeded.id)
        await service.complete_document_analysis(seeded.id)
        requested = await service.request_verification(seeded.id)
        assert requested.verification_id is not None
        await service.confirm_verification(requested.verification_id)
        await service.complete_risk_assessment(seeded.id)
        return seeded.id

    invoice_id = asyncio.run(scenario())

    invoice = service.get_invoice(invoice_id)
    assert invoice.status is InvoiceStatus.OFFER_READY
    assert invoice.risk_passport is not None
    assert invoice.risk_passport.eligibility.value == "ELIGIBLE"
    assert invoice.risk_passport.risk_score == 86
    assert invoice.risk_passport.suggested_advance_amount_usdc == 18_800


def test_seeded_analysis_requires_draft(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)

    async def scenario() -> None:
        seeded = await service.reset_demo()
        await service.analyze_seeded_documents(seeded.id)
        with pytest.raises(StateConflictError, match="DRAFT"):
            await service.analyze_seeded_documents(seeded.id)

    asyncio.run(scenario())


def test_reset_neutralises_an_in_flight_analysis(tmp_path: Path) -> None:
    """A background task from before the reset must not touch the reseeded invoice."""

    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)

    async def scenario() -> str:
        created = await service.create_invoice(uploads())
        # Reset before the scheduled analysis gets to run.
        seeded = await service.reset_demo()
        assert seeded.id == created.id  # the sequence restarts, so the id repeats
        await service.complete_document_analysis(created.id)
        return seeded.id

    invoice_id = asyncio.run(scenario())

    invoice = service.get_invoice(invoice_id)
    assert invoice.status is InvoiceStatus.DRAFT
    assert invoice.analysis is None
    assert invoice.documents == []
