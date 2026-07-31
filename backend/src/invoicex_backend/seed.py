"""Demo seed documents used to rebuild a runnable scenario without an upload."""

from __future__ import annotations

from pathlib import Path

from invoicex_backend.errors import DocumentValidationError
from invoicex_backend.models import DocumentType, UploadedDocument

SEED_FILE_NAMES: dict[DocumentType, str] = {
    document_type: f"{document_type.value}.pdf" for document_type in DocumentType
}


def load_seed_documents(directory: Path) -> list[UploadedDocument]:
    """Read the four demo PDFs so the Document Agent has real content to parse."""

    documents: list[UploadedDocument] = []
    for document_type, file_name in SEED_FILE_NAMES.items():
        path = directory / file_name
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise DocumentValidationError(
                f"데모 시드 문서를 읽을 수 없습니다: {path}"
            ) from exc
        if not data:
            raise DocumentValidationError(f"데모 시드 문서가 비어 있습니다: {path}")
        documents.append(
            UploadedDocument(
                type=document_type,
                file_name=file_name,
                mime_type="application/pdf",
                data=data,
            )
        )
    return documents
