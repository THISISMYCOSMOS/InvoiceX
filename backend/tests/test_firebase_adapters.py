from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from invoicex_backend.app import create_app
from invoicex_backend.models import (
    DocumentType,
    Invoice,
    InvoiceDocument,
    InvoiceParty,
    InvoiceStatus,
    UploadedDocument,
    UploadStatus,
    Verification,
    VerificationStatus,
)
from invoicex_backend.repository import FirestoreStateRepository
from invoicex_backend.service import InvoiceService
from invoicex_backend.storage import FirebaseDocumentStorage
from tests.conftest import mock_settings


class FakeSnapshot:
    def __init__(self, document_id: str, data: dict[str, Any]) -> None:
        self.id = document_id
        self._data = data

    def to_dict(self) -> dict[str, Any]:
        return self._data


class FakeDocumentReference:
    def __init__(self, collection: str, document_id: str) -> None:
        self.collection = collection
        self.id = document_id


class FakeCollection:
    def __init__(self, client: FakeFirestoreClient, name: str) -> None:
        self._client = client
        self._name = name

    def document(self, document_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._name, document_id)

    def stream(self) -> list[FakeSnapshot]:
        return [
            FakeSnapshot(document_id, data)
            for document_id, data in self._client.data.get(self._name, {}).items()
        ]


class FakeBatch:
    def __init__(self, client: FakeFirestoreClient) -> None:
        self._client = client
        self._writes: list[tuple[FakeDocumentReference, dict[str, Any]]] = []

    def set(
        self,
        reference: FakeDocumentReference,
        data: dict[str, Any],
    ) -> None:
        self._writes.append((reference, data))

    def commit(self) -> None:
        for reference, data in self._writes:
            self._client.data.setdefault(reference.collection, {})[reference.id] = data


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, dict[str, Any]]] = {}
        self.closed = False

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self, name)

    def batch(self) -> FakeBatch:
        return FakeBatch(self)

    def close(self) -> None:
        self.closed = True


class FakeBlob:
    def __init__(self, name: str) -> None:
        self.name = name
        self.data = b""
        self.content_type = ""

    def upload_from_string(self, data: bytes, *, content_type: str) -> None:
        self.data = data
        self.content_type = content_type

    def download_as_bytes(self) -> bytes:
        return self.data


class FakeBucket:
    name = "invoicex-demo.firebasestorage.app"

    def __init__(self) -> None:
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, name: str) -> FakeBlob:
        return self.blobs.setdefault(name, FakeBlob(name))


class FakeDownloadService:
    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def read_document(
        self,
        invoice_id: str,
        document_id: str,
    ) -> tuple[InvoiceDocument, bytes]:
        return (
            InvoiceDocument(
                id=document_id,
                invoice_id=invoice_id,
                type=DocumentType.INVOICE,
                file_name="../../invoice.pdf",
                mime_type="application/pdf",
                file_size=4,
                storage_url=f"http://testserver/uploads/{invoice_id}/{document_id}",
                upload_status=UploadStatus.COMPLETED,
            ),
            b"%PDF",
        )


def sample_invoice() -> Invoice:
    return Invoice(
        id="INV-2026-001",
        supplier=InvoiceParty(id="SUPPLIER_ALPHA", name="Alpha Components"),
        buyer=InvoiceParty(id="BUYER_PRIME", name="Prime Mobility"),
        investor=InvoiceParty(id="INVESTOR_NOVA", name="Nova Capital"),
        invoice_amount_krw=20_000_000,
        issue_date="2026-07-31",
        due_date="2026-10-29",
        delivery_date="2026-07-26",
        contract_number="CONTRACT-001",
        purchase_order_number="PO-001",
        status=InvoiceStatus.BUYER_REVIEW,
        verification_id="VER-2026-001",
        documents=[],
        analysis=None,
        risk_passport=None,
        funding_transaction=None,
        settlement_transaction=None,
        settlement=None,
        agent_traces=[],
    )


@pytest.mark.asyncio
async def test_firestore_repository_round_trips_aggregate_snapshots(
    tmp_path: Path,
) -> None:
    client = FakeFirestoreClient()
    repository = FirestoreStateRepository(mock_settings(tmp_path), client)
    invoice = sample_invoice()
    verification = Verification(
        id="VER-2026-001",
        invoice_id=invoice.id,
        status=VerificationStatus.PENDING,
    )

    await repository.save(invoice=invoice, verification=verification)
    restored = await repository.load()
    await repository.close()

    assert restored.invoices[invoice.id] == invoice
    assert restored.verifications[verification.id] == verification
    assert client.closed is True


@pytest.mark.asyncio
async def test_firebase_storage_uses_private_invoice_object_path(
    tmp_path: Path,
) -> None:
    bucket = FakeBucket()
    storage = FirebaseDocumentStorage(mock_settings(tmp_path), bucket)
    upload = UploadedDocument(
        type=DocumentType.INVOICE,
        file_name="../../invoice.pdf",
        mime_type="application/pdf",
        data=b"%PDF",
    )

    document = await storage.store(
        document_id="DOC-001",
        invoice_id="INV-2026-001",
        upload=upload,
    )

    object_name = "invoices/INV-2026-001/DOC-001.pdf"
    assert bucket.blobs[object_name].data == b"%PDF"
    assert document.storage_url == "http://testserver/uploads/INV-2026-001/DOC-001"
    assert await storage.read(document) == b"%PDF"


def test_private_upload_route_streams_document_without_openapi_changes(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings=mock_settings(tmp_path / "uploads"),
        service=cast(InvoiceService, FakeDownloadService()),
    )

    with TestClient(app) as client:
        response = client.get("/uploads/INV-2026-001/DOC-001")
        schema = client.get("/api/docs-json").json()

    assert response.status_code == 200
    assert response.content == b"%PDF"
    assert response.headers["content-disposition"] == (
        "inline; filename*=UTF-8''invoice.pdf"
    )
    assert "/uploads/{invoice_id}/{document_id}" not in schema["paths"]
