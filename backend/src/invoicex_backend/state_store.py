"""Restart-durable JSON snapshot of the Invoice aggregate state."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from invoicex_agents.models.document import DocumentAnalysisResult
from pydantic import BaseModel, ConfigDict, Field

from invoicex_backend.models import InvestorMandate, Invoice, Verification

logger = logging.getLogger(__name__)

STATE_SCHEMA_VERSION = 1


class PersistedState(BaseModel):
    """Everything InvoiceService must recover to continue a demo after a restart."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = STATE_SCHEMA_VERSION
    # Absent in files written before the mandate existed; None means "use the
    # environment default", so older snapshots still load.
    mandate: InvestorMandate | None = None
    invoices: dict[str, Invoice] = Field(default_factory=dict)
    verifications: dict[str, Verification] = Field(default_factory=dict)
    agent_analyses: dict[str, DocumentAnalysisResult] = Field(default_factory=dict)
    invoice_sequence: int = 0
    verification_sequence: int = 0
    document_sequence: int = 0
    trace_sequence: int = 0


class JsonStateStore:
    """Atomically replace a single JSON file holding the whole aggregate state.

    The demo keeps a handful of invoices, so a whole-state snapshot stays cheap
    and avoids the schema drift a relational mapping would introduce against the
    deeply nested frontend DTOs.
    """

    def __init__(self, path: Path) -> None:
        self._path = path.resolve()
        if self._path.is_dir():
            # Never let a directory become the snapshot target: _quarantine()
            # would rename it away.
            raise ValueError(f"상태 파일 경로가 디렉터리입니다: {self._path}")
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> PersistedState:
        """Return the stored state, or an empty one when it is absent or unusable."""

        if not self._path.exists():
            return PersistedState()
        try:
            state = PersistedState.model_validate_json(self._path.read_bytes())
        except (OSError, ValueError):
            logger.exception("상태 파일을 읽을 수 없어 빈 상태로 시작합니다: %s", self._path)
            self._quarantine()
            return PersistedState()

        if state.schema_version != STATE_SCHEMA_VERSION:
            logger.error(
                "상태 파일 schema_version %s는 지원하지 않아 빈 상태로 시작합니다: %s",
                state.schema_version,
                self._path,
            )
            self._quarantine()
            return PersistedState()
        return state

    def save(self, state: PersistedState) -> None:
        """Write the snapshot through a temporary file so readers never see a partial write."""

        temporary = self._path.with_name(f"{self._path.name}.tmp")
        try:
            temporary.write_text(state.model_dump_json(), encoding="utf-8")
            os.replace(temporary, self._path)
        except OSError:
            # A demo must keep serving from memory even when the disk rejects us.
            logger.exception("상태 저장에 실패했습니다: %s", self._path)
            temporary.unlink(missing_ok=True)

    def _quarantine(self) -> None:
        """Keep an unreadable state file for inspection instead of overwriting it."""

        try:
            os.replace(self._path, self._path.with_name(f"{self._path.name}.corrupt"))
        except OSError:
            logger.exception("손상된 상태 파일을 보관하지 못했습니다: %s", self._path)
