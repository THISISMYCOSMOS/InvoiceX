"""Local upload storage used by the Demo API."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from invoicex_backend.config import BackendSettings
from invoicex_backend.models import (
    InvoiceDocument,
    UploadedDocument,
    UploadStatus,
)


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
