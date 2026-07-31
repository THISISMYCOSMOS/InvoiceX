"""The Document Agent must run outside the upload request."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from invoicex_agents.exceptions import AgentError
from invoicex_agents.models.document import DocumentAnalysisResult

from invoicex_backend.agents import AgentDocument, MockAgentGateway
from invoicex_backend.app import create_app
from invoicex_backend.config import BackendSettings
from invoicex_backend.models import DocumentType, InvoiceStatus, UploadedDocument
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import create_solana_gateway
from invoicex_backend.state_store import JsonStateStore
from invoicex_backend.storage import LocalDocumentStorage
from tests.conftest import deterministic_pdf, mock_settings


class FailingDocumentAgentGateway(MockAgentGateway):
    """Reproduce a Gemini outage during the background analysis."""

    async def analyze_documents(
        self,
        invoice_id: str,
        documents: list[AgentDocument],
    ) -> DocumentAnalysisResult:
        raise AgentError("Gemini unavailable")


def build_service(
    settings: BackendSettings,
    agent_gateway: MockAgentGateway | None = None,
) -> InvoiceService:
    return InvoiceService(
        settings=settings,
        agent_gateway=agent_gateway or MockAgentGateway(),
        solana_gateway=create_solana_gateway(settings),
        storage=LocalDocumentStorage(settings),
        state_store=JsonStateStore(settings.resolved_state_file()),
    )


def uploads() -> list[UploadedDocument]:
    return [
        UploadedDocument(
            type=document_type,
            file_name=f"{document_type.value.lower()}.pdf",
            mime_type="application/pdf",
            data=deterministic_pdf(),
        )
        for document_type in DocumentType
    ]


def test_upload_returns_before_the_agent_runs(tmp_path: Path) -> None:
    """DOCUMENT_ANALYZING must be observable, or the frontend polling is dead code."""

    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)

    async def scenario() -> None:
        created = await service.create_invoice(uploads())
        assert created.status is InvoiceStatus.DOCUMENT_ANALYZING
        assert created.analysis is None
        assert len(created.documents) == 4

        # Whatever the frontend polls before the agent finishes sees the same.
        polled = service.get_invoice(created.id)
        assert polled.status is InvoiceStatus.DOCUMENT_ANALYZING

        await service.complete_document_analysis(created.id)
        finished = service.get_invoice(created.id)
        assert finished.status is InvoiceStatus.DOCUMENT_REVIEW_REQUIRED
        assert finished.analysis is not None
        assert finished.analysis.amount_krw.value == 20_000_000

    asyncio.run(scenario())


def test_background_analysis_failure_surfaces_as_error_with_a_trace(
    tmp_path: Path,
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings, FailingDocumentAgentGateway())

    async def scenario() -> str:
        created = await service.create_invoice(uploads())
        await service.complete_document_analysis(created.id)
        return created.id

    invoice_id = asyncio.run(scenario())

    failed = service.get_invoice(invoice_id)
    assert failed.status is InvoiceStatus.ERROR
    trace = failed.agent_traces[-1]
    assert trace.status == "FAILED"
    assert trace.source_agent == "DOCUMENT_AGENT"
    assert "Gemini" in trace.summary

    # The failure must be durable, not only in memory.
    assert build_service(settings).get_invoice(invoice_id).status is InvoiceStatus.ERROR


def test_analysis_is_not_run_twice(tmp_path: Path) -> None:
    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)

    async def scenario() -> str:
        created = await service.create_invoice(uploads())
        await service.complete_document_analysis(created.id)
        # A duplicated background task must be a no-op, not a second analysis.
        await service.complete_document_analysis(created.id)
        return created.id

    invoice_id = asyncio.run(scenario())

    invoice = service.get_invoice(invoice_id)
    assert invoice.status is InvoiceStatus.DOCUMENT_REVIEW_REQUIRED
    document_traces = [
        trace for trace in invoice.agent_traces if trace.source_agent == "DOCUMENT_AGENT"
    ]
    assert len(document_traces) == 1


def test_restart_during_analysis_does_not_strand_the_invoice(tmp_path: Path) -> None:
    """A restart loses the in-flight agent call, so the invoice must not stay pending."""

    settings = mock_settings(tmp_path / "uploads")
    service = build_service(settings)
    invoice_id = asyncio.run(service.create_invoice(uploads())).id
    assert service.get_invoice(invoice_id).status is InvoiceStatus.DOCUMENT_ANALYZING

    restarted = build_service(settings)

    recovered = restarted.get_invoice(invoice_id)
    assert recovered.status is InvoiceStatus.ERROR
    assert recovered.agent_traces[-1].status == "FAILED"
    assert "재시작" in recovered.agent_traces[-1].summary
    # And the recovery itself must be durable.
    assert build_service(settings).get_invoice(invoice_id).status is InvoiceStatus.ERROR


def test_restart_leaves_settled_invoices_untouched(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    """The recovery sweep must only touch transient statuses."""

    settings = mock_settings(tmp_path / "uploads")
    with TestClient(create_app(settings=settings)) as client:
        invoice_id = client.post("/api/v1/invoices", files=contract_files).json()[
            "invoice"
        ]["id"]
        verification_id = client.post(
            f"/api/v1/invoices/{invoice_id}/verification-request"
        ).json()["invoice"]["verificationId"]
        client.post(f"/api/v1/verifications/{verification_id}/confirm")

    restarted = build_service(settings)
    invoice = restarted.get_invoice(invoice_id)
    assert invoice.status is InvoiceStatus.OFFER_READY
    assert all(trace.status != "FAILED" for trace in invoice.agent_traces)
