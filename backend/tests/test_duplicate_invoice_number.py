from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from invoicex_agents.models.document import DocumentAnalysisResult

from invoicex_backend.agents import AgentDocument, MockAgentGateway
from invoicex_backend.app import create_app
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import create_solana_gateway
from invoicex_backend.storage import LocalDocumentStorage
from tests.conftest import mock_settings


class InvoiceNumberAgentGateway(MockAgentGateway):
    def __init__(self, invoice_numbers: list[str]) -> None:
        self._invoice_numbers = iter(invoice_numbers)

    async def analyze_documents(
        self,
        invoice_id: str,
        documents: list[AgentDocument],
    ) -> DocumentAnalysisResult:
        invoice_number = next(self._invoice_numbers)
        response = self._document_response(invoice_id, documents)
        for document in response["documents"]:
            if document["documentType"] != "INVOICE":
                continue
            document["extractedData"]["invoiceNumber"] = invoice_number
            for evidence in document["sourceEvidence"]:
                if evidence["field"] == "invoiceNumber":
                    evidence["quote"] = invoice_number
        return DocumentAnalysisResult.model_validate(response)


def test_only_an_exact_duplicate_invoice_number_is_blocked(
    tmp_path: Path,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    settings = mock_settings(tmp_path / "uploads")
    storage = LocalDocumentStorage(settings)
    service = InvoiceService(
        settings=settings,
        agent_gateway=InvoiceNumberAgentGateway(
            ["INV-DUPLICATE-001", "INV-DUPLICATE-001", "INV-DIFFERENT-002"]
        ),
        solana_gateway=create_solana_gateway(settings),
        storage=storage,
    )
    app = create_app(settings=settings, service=service)

    with TestClient(app) as client:
        first = client.post("/api/v1/invoices", files=contract_files)
        duplicate = client.post("/api/v1/invoices", files=contract_files)
        different_number = client.post("/api/v1/invoices", files=contract_files)

        assert first.status_code == 201
        assert first.json()["invoice"]["status"] == "DOCUMENT_REVIEW_REQUIRED"

        assert duplicate.status_code == 201
        assert duplicate.json()["invoice"]["status"] == "BLOCKED"
        assert duplicate.json()["invoice"]["rejectionReasonCode"] == "DUPLICATE_INVOICE"

        assert different_number.status_code == 201
        assert different_number.json()["invoice"]["status"] == "DOCUMENT_REVIEW_REQUIRED"
        assert different_number.json()["invoice"]["rejectionReasonCode"] is None

        first_invoice_id = first.json()["invoice"]["id"]
        requested = client.post(
            f"/api/v1/invoices/{first_invoice_id}/verification-request"
        )
        verification_id = requested.json()["invoice"]["verificationId"]
        confirmed = client.post(f"/api/v1/verifications/{verification_id}/confirm")

        assert confirmed.status_code == 200
        assert confirmed.json()["invoice"]["status"] == "OFFER_READY"
