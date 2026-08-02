"""Local upload storage used by the Demo API."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import (
    InvoiceDocument,
    UploadedDocument,
    UploadStatus,
)


class DocumentStorage(Protocol):
    """Document persistence boundary for local and Cloud Storage adapters."""

    async def store(
        self,
        *,
        document_id: str,
        invoice_id: str,
        upload: UploadedDocument,
    ) -> InvoiceDocument: ...

    def presentation_url(self, document: InvoiceDocument) -> str: ...


class LocalDocumentStorage:
    """Persist validated uploads under a non-user-controlled filename."""

    def __init__(self, settings: BackendSettings) -> None:
        self._directory = settings.upload_directory.resolve()
        self._public_base_url = settings.public_base_url.rstrip("/")
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    async def store(
        self,
        *,
        document_id: str,
        invoice_id: str,
        upload: UploadedDocument,
    ) -> InvoiceDocument:
        extension = self._safe_extension(upload.file_name, upload.mime_type)
        stored_name = f"{uuid4().hex}{extension}"
        target = self._directory / stored_name
        await asyncio.to_thread(target.write_bytes, upload.data)
        return InvoiceDocument(
            id=document_id,
            invoice_id=invoice_id,
            type=upload.type,
            file_name=upload.file_name,
            mime_type=upload.mime_type,
            file_size=len(upload.data),
            storage_url=f"{self._public_base_url}/uploads/{stored_name}",
            upload_status=UploadStatus.COMPLETED,
        )

    def presentation_url(self, document: InvoiceDocument) -> str:
        return document.storage_url

    @staticmethod
    def _safe_extension(file_name: str, mime_type: str) -> str:
        expected = {
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
        }
        extension = Path(file_name).suffix.lower()
        return extension if extension in {".pdf", ".jpg", ".jpeg", ".png"} else expected[mime_type]


class GcsDocumentStorage:
    """Private GCS document storage with short-lived download URLs.

    The persisted `storage_url` is a stable `gs://` reference. API responses are
    enriched with a signed URL only when an invoice is read, so expired URLs are
    never stored in Cloud SQL.
    """

    def __init__(self, settings: BackendSettings, client: object | None = None) -> None:
        if not settings.gcs_document_bucket:
            raise ValueError("GCS_DOCUMENT_BUCKET is required for GcsDocumentStorage")
        if client is None:
            from google.cloud import storage

            client = storage.Client(project=settings.gcp_project_id)
        self._bucket_name = settings.gcs_document_bucket
        self._bucket = client.bucket(self._bucket_name)  # type: ignore[attr-defined]
        self._prefix = settings.gcs_document_prefix.strip("/")
        self._signed_url_ttl = timedelta(seconds=settings.gcs_signed_url_ttl_seconds)

    async def store(
        self,
        *,
        document_id: str,
        invoice_id: str,
        upload: UploadedDocument,
    ) -> InvoiceDocument:
        extension = LocalDocumentStorage._safe_extension(upload.file_name, upload.mime_type)
        object_name = "/".join(
            part
            for part in (
                self._prefix,
                invoice_id,
                document_id,
                f"{uuid4().hex}{extension}",
            )
            if part
        )
        blob = self._bucket.blob(object_name)
        await asyncio.to_thread(
            blob.upload_from_string,
            upload.data,
            content_type=upload.mime_type,
        )
        return InvoiceDocument(
            id=document_id,
            invoice_id=invoice_id,
            type=upload.type,
            file_name=upload.file_name,
            mime_type=upload.mime_type,
            file_size=len(upload.data),
            storage_url=f"gs://{self._bucket_name}/{object_name}",
            upload_status=UploadStatus.COMPLETED,
        )

    def presentation_url(self, document: InvoiceDocument) -> str:
        prefix = f"gs://{self._bucket_name}/"
        if not document.storage_url.startswith(prefix):
            raise ValueError("Document is not stored in the configured GCS bucket")
        object_name = document.storage_url.removeprefix(prefix)
        safe_file_name = (
            Path(document.file_name).name.replace('"', "").replace("\r", "").replace("\n", "")
            or "document"
        )
        return self._bucket.blob(object_name).generate_signed_url(
            version="v4",
            expiration=self._signed_url_ttl,
            method="GET",
            response_disposition=f'inline; filename="{safe_file_name}"',
        )
