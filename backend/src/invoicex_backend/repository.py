"""Durable domain records behind a replaceable repository boundary.

SQLite is deliberately the first adapter for local Devnet demos. The service
depends only on this small interface so a Cloud SQL implementation can replace
it without changing mandate, vault, or RWA execution logic.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Protocol

from invoicex_agents.models.document import DocumentAnalysisResult

from invoicex_backend.models import (
    AgentDecision,
    InvestorMandate,
    Invoice,
    RwaAsset,
    VaultBalance,
    Verification,
)


class RwaRepository(Protocol):
    def close(self) -> None: ...
    def save_mandate(self, mandate: InvestorMandate) -> None: ...
    def active_mandates(self) -> list[InvestorMandate]: ...
    def save_vault(self, vault: VaultBalance) -> None: ...
    def get_vault(self, owner_wallet_address: str) -> VaultBalance | None: ...
    def save_rwa_asset(self, asset: RwaAsset) -> None: ...
    def get_rwa_asset(self, invoice_id: str) -> RwaAsset | None: ...
    def save_decision(self, decision: AgentDecision) -> None: ...
    def get_decision(self, invoice_id: str) -> AgentDecision | None: ...
    def save_supplier_wallet(self, wallet_address: str) -> None: ...
    def get_supplier_wallet(self) -> str | None: ...
    def claim_execution(self, invoice_id: str) -> bool: ...
    def finish_execution(self, invoice_id: str, status: str) -> None: ...
    def claim_deposit(self, signature: str) -> bool: ...
    def committed_for_mandate(self, mandate_id: str) -> int: ...
    def save_invoice(self, invoice: Invoice) -> None: ...
    def list_invoices(self) -> list[Invoice]: ...
    def save_analysis(self, invoice_id: str, analysis: DocumentAnalysisResult) -> None: ...
    def list_analyses(self) -> dict[str, DocumentAnalysisResult]: ...
    def save_verification(self, verification: Verification) -> None: ...
    def list_verifications(self) -> list[Verification]: ...


class SQLiteRwaRepository:
    """Thread-safe SQLite implementation used for local development and demos."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS mandates (
                    id TEXT PRIMARY KEY,
                    owner_wallet_address TEXT NOT NULL,
                    status TEXT NOT NULL,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vaults (
                    owner_wallet_address TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rwa_assets (
                    invoice_id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_decisions (
                    invoice_id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS profile_wallets (
                    role TEXT PRIMARY KEY,
                    wallet_address TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS execution_claims (
                    invoice_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deposit_receipts (
                    signature TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS document_analyses (
                    invoice_id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS verifications (
                    id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _encode(value: object) -> str:
        return json.dumps(value.model_dump(mode="json"), separators=(",", ":"))  # type: ignore[attr-defined]

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def save_mandate(self, mandate: InvestorMandate) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                UPDATE mandates
                SET status = 'REVOKED'
                WHERE owner_wallet_address = ? AND id <> ? AND status = 'ACTIVE'
                """,
                (mandate.owner_wallet_address, mandate.id),
            )
            self._connection.execute(
                """
                INSERT OR REPLACE INTO mandates
                (id, owner_wallet_address, status, document) VALUES (?, ?, ?, ?)
                """,
                (
                    mandate.id,
                    mandate.owner_wallet_address,
                    mandate.status,
                    self._encode(mandate),
                ),
            )

    def active_mandates(self) -> list[InvestorMandate]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM mandates WHERE status = 'ACTIVE' ORDER BY rowid ASC"
            ).fetchall()
        return [InvestorMandate.model_validate_json(row["document"]) for row in rows]

    def save_vault(self, vault: VaultBalance) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO vaults (owner_wallet_address, document) VALUES (?, ?)",
                (vault.owner_wallet_address, self._encode(vault)),
            )

    def get_vault(self, owner_wallet_address: str) -> VaultBalance | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM vaults WHERE owner_wallet_address = ?",
                (owner_wallet_address,),
            ).fetchone()
        return VaultBalance.model_validate_json(row["document"]) if row else None

    def save_rwa_asset(self, asset: RwaAsset) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO rwa_assets (invoice_id, document) VALUES (?, ?)",
                (asset.invoice_id, self._encode(asset)),
            )

    def get_rwa_asset(self, invoice_id: str) -> RwaAsset | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM rwa_assets WHERE invoice_id = ?", (invoice_id,)
            ).fetchone()
        return RwaAsset.model_validate_json(row["document"]) if row else None

    def save_decision(self, decision: AgentDecision) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO agent_decisions (invoice_id, document) VALUES (?, ?)",
                (decision.invoice_id, self._encode(decision)),
            )

    def get_decision(self, invoice_id: str) -> AgentDecision | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM agent_decisions WHERE invoice_id = ?", (invoice_id,)
            ).fetchone()
        return AgentDecision.model_validate_json(row["document"]) if row else None

    def save_supplier_wallet(self, wallet_address: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO profile_wallets (role, wallet_address)
                VALUES ('SUPPLIER', ?)
                """,
                (wallet_address,),
            )

    def get_supplier_wallet(self) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT wallet_address FROM profile_wallets WHERE role = 'SUPPLIER'"
            ).fetchone()
        return str(row["wallet_address"]) if row else None

    def claim_execution(self, invoice_id: str) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO execution_claims (invoice_id, status) VALUES (?, 'RUNNING')
                ON CONFLICT(invoice_id) DO UPDATE SET status = 'RUNNING'
                WHERE execution_claims.status IN ('WAITING', 'FAILED')
                """,
                (invoice_id,),
            )
            if cursor.rowcount == 0:
                return False
        return True

    def finish_execution(self, invoice_id: str, status: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE execution_claims SET status = ? WHERE invoice_id = ?", (status, invoice_id)
            )

    def claim_deposit(self, signature: str) -> bool:
        with self._lock, self._connection:
            try:
                self._connection.execute(
                    "INSERT INTO deposit_receipts (signature) VALUES (?)",
                    (signature,),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def committed_for_mandate(self, mandate_id: str) -> int:
        with self._lock:
            rows = self._connection.execute("SELECT document FROM agent_decisions").fetchall()
        decisions = [AgentDecision.model_validate_json(row["document"]) for row in rows]
        return sum(
            decision.amount_usdc
            for decision in decisions
            if decision.mandate_id == mandate_id and decision.status in {"APPROVED", "EXECUTED"}
        )

    def save_invoice(self, invoice: Invoice) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO invoices (id, document) VALUES (?, ?)",
                (invoice.id, self._encode(invoice)),
            )

    def list_invoices(self) -> list[Invoice]:
        with self._lock:
            rows = self._connection.execute("SELECT document FROM invoices").fetchall()
        return [Invoice.model_validate_json(row["document"]) for row in rows]

    def save_analysis(self, invoice_id: str, analysis: DocumentAnalysisResult) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO document_analyses (invoice_id, document) VALUES (?, ?)",
                (invoice_id, self._encode(analysis)),
            )

    def list_analyses(self) -> dict[str, DocumentAnalysisResult]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT invoice_id, document FROM document_analyses"
            ).fetchall()
        return {
            row["invoice_id"]: DocumentAnalysisResult.model_validate_json(row["document"])
            for row in rows
        }

    def save_verification(self, verification: Verification) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO verifications (id, document) VALUES (?, ?)",
                (verification.id, self._encode(verification)),
            )

    def list_verifications(self) -> list[Verification]:
        with self._lock:
            rows = self._connection.execute("SELECT document FROM verifications").fetchall()
        return [Verification.model_validate_json(row["document"]) for row in rows]
