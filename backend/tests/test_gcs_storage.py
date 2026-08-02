from __future__ import annotations

import pytest

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import DocumentType, UploadedDocument
from invoicex_backend.storage import GcsDocumentStorage


class _FakeBlob:
    def __init__(self, name: str) -> None:
        self.name = name
        self.uploaded: tuple[bytes, str] | None = None
        self.signed_url_arguments: dict[str, object] | None = None

    def upload_from_string(self, data: bytes, content_type: str) -> None:
        self.uploaded = (data, content_type)

    def generate_signed_url(self, **kwargs: object) -> str:
        self.signed_url_arguments = kwargs
        return f"https://storage.example.test/{self.name}?signed=true"


class _FakeBucket:
    def __init__(self) -> None:
        self.blobs: dict[str, _FakeBlob] = {}

    def blob(self, name: str) -> _FakeBlob:
        return self.blobs.setdefault(name, _FakeBlob(name))


class _FakeStorageClient:
    def __init__(self) -> None:
        self.bucket_instance = _FakeBucket()

    def bucket(self, _: str) -> _FakeBucket:
        return self.bucket_instance


class _FakeSigningCredentials:
    def __init__(self) -> None:
        self.token = "short-lived-access-token"
        self.refresh_request: object | None = None

    def refresh(self, request: object) -> None:
        self.refresh_request = request


@pytest.mark.asyncio
async def test_gcs_storage_persists_private_object_and_generates_read_url() -> None:
    settings = BackendSettings(
        _env_file=None,
        DOCUMENT_STORAGE_BACKEND="gcs",
        GCS_DOCUMENT_BUCKET="invoicex-documents",
        GCS_DOCUMENT_PREFIX="invoice-files",
    )
    client = _FakeStorageClient()
    storage = GcsDocumentStorage(settings, client=client)
    document = await storage.store(
        document_id="DOC-001",
        invoice_id="INV-2026-001",
        upload=UploadedDocument(
            type=DocumentType.INVOICE,
            file_name="invoice.pdf",
            mime_type="application/pdf",
            data=b"%PDF-1.4",
        ),
    )

    assert document.storage_url.startswith(
        "gs://invoicex-documents/invoice-files/INV-2026-001/DOC-001/"
    )
    assert storage.presentation_url(document).endswith("?signed=true")
    blob = next(iter(client.bucket_instance.blobs.values()))
    assert blob.uploaded == (b"%PDF-1.4", "application/pdf")


@pytest.mark.asyncio
async def test_gcs_storage_uses_iam_signing_for_cloud_run_credentials() -> None:
    settings = BackendSettings(
        _env_file=None,
        DOCUMENT_STORAGE_BACKEND="gcs",
        GCS_DOCUMENT_BUCKET="invoicex-documents",
        GCS_SIGNING_SERVICE_ACCOUNT="invoicex-api@example.iam.gserviceaccount.com",
    )
    client = _FakeStorageClient()
    credentials = _FakeSigningCredentials()
    request = object()
    storage = GcsDocumentStorage(
        settings,
        client=client,
        signing_credentials=credentials,  # type: ignore[arg-type]
        signing_request=request,  # type: ignore[arg-type]
    )
    document = await storage.store(
        document_id="DOC-001",
        invoice_id="INV-2026-001",
        upload=UploadedDocument(
            type=DocumentType.INVOICE,
            file_name="invoice.pdf",
            mime_type="application/pdf",
            data=b"%PDF-1.4",
        ),
    )

    assert storage.presentation_url(document).endswith("?signed=true")
    blob = next(iter(client.bucket_instance.blobs.values()))
    assert blob.signed_url_arguments is not None
    assert blob.signed_url_arguments["service_account_email"] == (
        "invoicex-api@example.iam.gserviceaccount.com"
    )
    assert blob.signed_url_arguments["access_token"] == "short-lived-access-token"
    assert credentials.refresh_request is request
