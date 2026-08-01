"""Invoice aggregate persistence backed by memory or Cloud Firestore."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

from invoicex_agents.models.document import DocumentAnalysisResult

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import IntegrationError
from invoicex_backend.models import Invoice, Verification


@dataclass
class RepositoryState:
    """State restored when an API process starts."""

    invoices: dict[str, Invoice] = field(default_factory=dict)
    analyses: dict[str, DocumentAnalysisResult] = field(default_factory=dict)
    verifications: dict[str, Verification] = field(default_factory=dict)


class StateRepository(Protocol):
    """Persistence contract used by the domain service."""

    async def load(self) -> RepositoryState:
        """Load all MVP aggregates required by the in-process service."""

    async def save(
        self,
        *,
        invoice: Invoice | None = None,
        analysis: DocumentAnalysisResult | None = None,
        verification: Verification | None = None,
    ) -> None:
        """Atomically persist the supplied aggregate snapshots."""

    async def close(self) -> None:
        """Release provider resources."""


class MemoryStateRepository:
    """No-op persistence for deterministic local development and tests."""

    async def load(self) -> RepositoryState:
        return RepositoryState()

    async def save(
        self,
        *,
        invoice: Invoice | None = None,
        analysis: DocumentAnalysisResult | None = None,
        verification: Verification | None = None,
    ) -> None:
        return None

    async def close(self) -> None:
        return None


class FirestoreStateRepository:
    """Persist API aggregates in Firebase Cloud Firestore."""

    def __init__(self, settings: BackendSettings, client: Any) -> None:
        prefix = settings.firebase_collection_prefix
        self._client = client
        self._invoice_collection = f"{prefix}_invoices"
        self._analysis_collection = f"{prefix}_document_analyses"
        self._verification_collection = f"{prefix}_verifications"

    async def load(self) -> RepositoryState:
        try:
            return await asyncio.to_thread(self._load_sync)
        except IntegrationError:
            raise
        except Exception as exc:
            raise IntegrationError("Failed to restore InvoiceX state from Firestore.") from exc

    async def save(
        self,
        *,
        invoice: Invoice | None = None,
        analysis: DocumentAnalysisResult | None = None,
        verification: Verification | None = None,
    ) -> None:
        if invoice is None and analysis is None and verification is None:
            return
        if analysis is not None and invoice is None:
            raise ValueError("analysis persistence requires its invoice aggregate")
        try:
            await asyncio.to_thread(
                self._save_sync,
                invoice,
                analysis,
                verification,
            )
        except Exception as exc:
            raise IntegrationError("Failed to persist InvoiceX state to Firestore.") from exc

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            await asyncio.to_thread(close)

    def _load_sync(self) -> RepositoryState:
        invoices = {
            snapshot.id: Invoice.model_validate(snapshot.to_dict())
            for snapshot in self._client.collection(self._invoice_collection).stream()
        }
        analyses = {
            snapshot.id: DocumentAnalysisResult.model_validate(snapshot.to_dict())
            for snapshot in self._client.collection(self._analysis_collection).stream()
        }
        verifications = {
            snapshot.id: Verification.model_validate(snapshot.to_dict())
            for snapshot in self._client.collection(self._verification_collection).stream()
        }
        return RepositoryState(
            invoices=invoices,
            analyses=analyses,
            verifications=verifications,
        )

    def _save_sync(
        self,
        invoice: Invoice | None,
        analysis: DocumentAnalysisResult | None,
        verification: Verification | None,
    ) -> None:
        batch = self._client.batch()
        if invoice is not None:
            batch.set(
                self._client.collection(self._invoice_collection).document(invoice.id),
                invoice.model_dump(mode="json", by_alias=True),
            )
        if analysis is not None:
            batch.set(
                self._client.collection(self._analysis_collection).document(invoice.id),
                analysis.model_dump(mode="json", by_alias=True),
            )
        if verification is not None:
            batch.set(
                self._client.collection(self._verification_collection).document(
                    verification.id
                ),
                verification.model_dump(mode="json", by_alias=True),
            )
        batch.commit()
