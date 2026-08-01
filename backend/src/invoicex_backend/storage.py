"""Document storage adapters for local development and Firebase."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import uuid4

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import IntegrationError
from invoicex_backend.models import (
    InvoiceDocument,
    UploadedDocument,
    UploadStatus,
)


class DocumentStorage(Protocol):
    """Storage contract used by the Invoice service."""

    @property
    def directory(self) -> Path | None:
        """Return a local directory that FastAPI should expose, when applicable."""

    async def store(
        self,
        *,
        document_id: str,
        invoice_id: str,
        upload: UploadedDocument,
    ) -> InvoiceDocument:
        """Persist one validated upload."""

    async def read(self, document: InvoiceDocument) -> bytes:
        """Read an uploaded document through the trusted backend."""


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

    async def read(self, document: InvoiceDocument) -> bytes:
        stored_name = Path(urlsplit(document.storage_url).path).name
        target = (self._directory / stored_name).resolve()
        if target.parent != self._directory:
            raise IntegrationError("Invalid local document storage path.")
        try:
            return await asyncio.to_thread(target.read_bytes)
        except OSError as exc:
            raise IntegrationError("Failed to read the uploaded document.") from exc

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


class FirebaseDocumentStorage:
    """Store private invoice evidence in Cloud Storage for Firebase."""

    def __init__(self, settings: BackendSettings, bucket: Any) -> None:
        self._bucket = bucket
        self._public_base_url = settings.public_base_url.rstrip("/")

    @property
    def directory(self) -> None:
        return None

    async def store(
        self,
        *,
        document_id: str,
        invoice_id: str,
        upload: UploadedDocument,
    ) -> InvoiceDocument:
        extension = LocalDocumentStorage._safe_extension(
            upload.file_name,
            upload.mime_type,
        )
        object_name = f"invoices/{invoice_id}/{document_id}{extension}"
        try:
            await asyncio.to_thread(
                self._upload,
                object_name,
                upload,
            )
        except Exception as exc:
            raise IntegrationError(
                "Failed to upload invoice evidence to Firebase Storage."
            ) from exc

        return InvoiceDocument(
            id=document_id,
            invoice_id=invoice_id,
            type=upload.type,
            file_name=upload.file_name,
            mime_type=upload.mime_type,
            file_size=len(upload.data),
            storage_url=f"{self._public_base_url}/uploads/{invoice_id}/{document_id}",
            upload_status=UploadStatus.COMPLETED,
        )

    async def read(self, document: InvoiceDocument) -> bytes:
        extension = LocalDocumentStorage._safe_extension(
            document.file_name,
            document.mime_type,
        )
        object_name = f"invoices/{document.invoice_id}/{document.id}{extension}"
        try:
            return await asyncio.to_thread(
                self._bucket.blob(object_name).download_as_bytes
            )
        except Exception as exc:
            raise IntegrationError(
                "Failed to read invoice evidence from Firebase Storage."
            ) from exc

    def _upload(self, object_name: str, upload: UploadedDocument) -> None:
        blob = self._bucket.blob(object_name)
        blob.upload_from_string(upload.data, content_type=upload.mime_type)
