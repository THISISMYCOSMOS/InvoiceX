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

from invoicex_backend.config import BackendSettings
from invoicex_backend.agent_activity import AgentHandoff, AgentRun, AgentToolCall
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
    def save_agent_run(self, run: AgentRun) -> None: ...
    def get_agent_run(self, run_id: str) -> AgentRun | None: ...
    def list_agent_runs(self, invoice_id: str) -> list[AgentRun]: ...
    def save_agent_tool_call(self, call: AgentToolCall) -> None: ...
    def list_agent_tool_calls(self, run_id: str) -> list[AgentToolCall]: ...
    def save_agent_handoff(self, handoff: AgentHandoff) -> None: ...
    def list_agent_handoffs(self, run_id: str) -> list[AgentHandoff]: ...


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
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    invoice_id TEXT NOT NULL,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_tool_calls (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_handoffs (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
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

    def save_agent_run(self, run: AgentRun) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO agent_runs (id, invoice_id, document) VALUES (?, ?, ?)",
                (run.id, run.invoice_id, self._encode(run)),
            )

    def get_agent_run(self, run_id: str) -> AgentRun | None:
        with self._lock:
            row = self._connection.execute("SELECT document FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        return AgentRun.model_validate_json(row["document"]) if row else None

    def list_agent_runs(self, invoice_id: str) -> list[AgentRun]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM agent_runs WHERE invoice_id = ? ORDER BY id", (invoice_id,)
            ).fetchall()
        return [AgentRun.model_validate_json(row["document"]) for row in rows]

    def save_agent_tool_call(self, call: AgentToolCall) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO agent_tool_calls (id, run_id, sequence, document) VALUES (?, ?, ?, ?)",
                (call.id, call.run_id, call.sequence, self._encode(call)),
            )

    def list_agent_tool_calls(self, run_id: str) -> list[AgentToolCall]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM agent_tool_calls WHERE run_id = ? ORDER BY sequence", (run_id,)
            ).fetchall()
        return [AgentToolCall.model_validate_json(row["document"]) for row in rows]

    def save_agent_handoff(self, handoff: AgentHandoff) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO agent_handoffs (id, run_id, document) VALUES (?, ?, ?)",
                (handoff.id, handoff.run_id, self._encode(handoff)),
            )

    def list_agent_handoffs(self, run_id: str) -> list[AgentHandoff]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM agent_handoffs WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [AgentHandoff.model_validate_json(row["document"]) for row in rows]


class CloudSqlRwaRepository:
    """PostgreSQL adapter used by the Cloud Run deployment.

    Domain payloads deliberately remain JSON documents, matching the SQLite
    adapter. This keeps the backend's aggregate boundary stable while Cloud SQL
    supplies durable, cross-restart records and atomic uniqueness constraints.
    """

    _schema_statements = (
        """
        CREATE TABLE IF NOT EXISTS mandates (
            id TEXT PRIMARY KEY,
            owner_wallet_address TEXT NOT NULL,
            status TEXT NOT NULL,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS vaults (
            owner_wallet_address TEXT PRIMARY KEY,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS rwa_assets (
            invoice_id TEXT PRIMARY KEY,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_decisions (
            invoice_id TEXT PRIMARY KEY,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS profile_wallets (
            role TEXT PRIMARY KEY,
            wallet_address TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS execution_claims (
            invoice_id TEXT PRIMARY KEY,
            status TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS deposit_receipts (
            signature TEXT PRIMARY KEY
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS document_analyses (
            invoice_id TEXT PRIMARY KEY,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS verifications (
            id TEXT PRIMARY KEY,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_tool_calls (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            document JSONB NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_handoffs (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            document JSONB NOT NULL
        )
        """,
    )

    def __init__(self, connection: object, connector: object | None = None) -> None:
        self._connection = connection
        self._connector = connector
        self._lock = threading.RLock()
        self._ensure_schema()

    @classmethod
    def from_settings(cls, settings: BackendSettings) -> CloudSqlRwaRepository:
        """Connect through Cloud SQL's IAM-authenticated Python connector."""

        from google.cloud.sql.connector import Connector, IPTypes

        connector = Connector()
        ip_type = IPTypes.PRIVATE if settings.cloud_sql_ip_type == "private" else IPTypes.PUBLIC
        connection = connector.connect(
            settings.cloud_sql_instance_connection_name,
            "pg8000",
            user=settings.cloud_sql_user,
            password=settings.cloud_sql_password,
            db=settings.cloud_sql_database,
            ip_type=ip_type,
        )
        return cls(connection, connector)

    @staticmethod
    def _encode(value: object) -> str:
        return json.dumps(value.model_dump(mode="json"), separators=(",", ":"))  # type: ignore[attr-defined]

    @staticmethod
    def _decode(model: type[object], value: object) -> object:
        if isinstance(value, (bytes, bytearray)):
            value = value.decode("utf-8")
        if isinstance(value, str):
            return model.model_validate_json(value)  # type: ignore[attr-defined]
        return model.model_validate(value)  # type: ignore[attr-defined]

    def _ensure_schema(self) -> None:
        self._write(
            lambda cursor: [cursor.execute(statement) for statement in self._schema_statements]
        )

    def _write(self, operation: object) -> object:
        with self._lock:
            cursor = self._connection.cursor()  # type: ignore[attr-defined]
            try:
                result = operation(cursor)  # type: ignore[operator]
                self._connection.commit()  # type: ignore[attr-defined]
                return result
            except Exception:
                self._connection.rollback()  # type: ignore[attr-defined]
                raise
            finally:
                cursor.close()

    def _read_one(self, query: str, params: tuple[object, ...]) -> tuple[object, ...] | None:
        with self._lock:
            cursor = self._connection.cursor()  # type: ignore[attr-defined]
            try:
                cursor.execute(query, params)
                return cursor.fetchone()
            finally:
                cursor.close()

    def _read_all(self, query: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
        with self._lock:
            cursor = self._connection.cursor()  # type: ignore[attr-defined]
            try:
                cursor.execute(query, params)
                return list(cursor.fetchall())
            finally:
                cursor.close()

    def close(self) -> None:
        with self._lock:
            self._connection.close()  # type: ignore[attr-defined]
            if self._connector is not None:
                self._connector.close()  # type: ignore[attr-defined]

    def save_mandate(self, mandate: InvestorMandate) -> None:
        def write(cursor: object) -> None:
            cursor.execute(  # type: ignore[attr-defined]
                """
                UPDATE mandates SET status = 'REVOKED'
                WHERE owner_wallet_address = %s AND id <> %s AND status = 'ACTIVE'
                """,
                (mandate.owner_wallet_address, mandate.id),
            )
            cursor.execute(  # type: ignore[attr-defined]
                """
                INSERT INTO mandates (id, owner_wallet_address, status, document)
                VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    owner_wallet_address = EXCLUDED.owner_wallet_address,
                    status = EXCLUDED.status,
                    document = EXCLUDED.document
                """,
                (mandate.id, mandate.owner_wallet_address, mandate.status, self._encode(mandate)),
            )

        self._write(write)

    def active_mandates(self) -> list[InvestorMandate]:
        rows = self._read_all("SELECT document FROM mandates WHERE status = 'ACTIVE' ORDER BY id")
        return [self._decode(InvestorMandate, row[0]) for row in rows]  # type: ignore[list-item]

    def save_vault(self, vault: VaultBalance) -> None:
        self._upsert_document(
            "vaults", "owner_wallet_address", vault.owner_wallet_address, vault
        )

    def get_vault(self, owner_wallet_address: str) -> VaultBalance | None:
        row = self._read_one(
            "SELECT document FROM vaults WHERE owner_wallet_address = %s", (owner_wallet_address,)
        )
        return self._decode(VaultBalance, row[0]) if row else None  # type: ignore[return-value]

    def save_rwa_asset(self, asset: RwaAsset) -> None:
        self._upsert_document("rwa_assets", "invoice_id", asset.invoice_id, asset)

    def get_rwa_asset(self, invoice_id: str) -> RwaAsset | None:
        row = self._read_one("SELECT document FROM rwa_assets WHERE invoice_id = %s", (invoice_id,))
        return self._decode(RwaAsset, row[0]) if row else None  # type: ignore[return-value]

    def save_decision(self, decision: AgentDecision) -> None:
        self._upsert_document("agent_decisions", "invoice_id", decision.invoice_id, decision)

    def get_decision(self, invoice_id: str) -> AgentDecision | None:
        row = self._read_one(
            "SELECT document FROM agent_decisions WHERE invoice_id = %s", (invoice_id,)
        )
        return self._decode(AgentDecision, row[0]) if row else None  # type: ignore[return-value]

    def save_supplier_wallet(self, wallet_address: str) -> None:
        self._write(
            lambda cursor: cursor.execute(  # type: ignore[attr-defined]
                """
                INSERT INTO profile_wallets (role, wallet_address) VALUES ('SUPPLIER', %s)
                ON CONFLICT (role) DO UPDATE SET wallet_address = EXCLUDED.wallet_address
                """,
                (wallet_address,),
            )
        )

    def get_supplier_wallet(self) -> str | None:
        row = self._read_one(
            "SELECT wallet_address FROM profile_wallets WHERE role = 'SUPPLIER'", ()
        )
        return str(row[0]) if row else None

    def claim_execution(self, invoice_id: str) -> bool:
        row = self._write(
            lambda cursor: (
                cursor.execute(  # type: ignore[attr-defined]
                    """
                    INSERT INTO execution_claims (invoice_id, status) VALUES (%s, 'RUNNING')
                    ON CONFLICT (invoice_id) DO UPDATE SET status = 'RUNNING'
                    WHERE execution_claims.status IN ('WAITING', 'FAILED')
                    RETURNING invoice_id
                    """,
                    (invoice_id,),
                ),
                cursor.fetchone(),  # type: ignore[attr-defined]
            )[1]
        )
        return row is not None

    def finish_execution(self, invoice_id: str, status: str) -> None:
        self._write(
            lambda cursor: cursor.execute(  # type: ignore[attr-defined]
                "UPDATE execution_claims SET status = %s WHERE invoice_id = %s",
                (status, invoice_id),
            )
        )

    def claim_deposit(self, signature: str) -> bool:
        row = self._write(
            lambda cursor: (
                cursor.execute(  # type: ignore[attr-defined]
                    """
                    INSERT INTO deposit_receipts (signature) VALUES (%s)
                    ON CONFLICT (signature) DO NOTHING
                    RETURNING signature
                    """,
                    (signature,),
                ),
                cursor.fetchone(),  # type: ignore[attr-defined]
            )[1]
        )
        return row is not None

    def committed_for_mandate(self, mandate_id: str) -> int:
        rows = self._read_all("SELECT document FROM agent_decisions")
        decisions = [self._decode(AgentDecision, row[0]) for row in rows]
        return sum(
            decision.amount_usdc
            for decision in decisions
            if decision.mandate_id == mandate_id and decision.status in {"APPROVED", "EXECUTED"}
        )

    def save_invoice(self, invoice: Invoice) -> None:
        self._upsert_document("invoices", "id", invoice.id, invoice)

    def list_invoices(self) -> list[Invoice]:
        return [
            self._decode(Invoice, row[0])  # type: ignore[list-item]
            for row in self._read_all("SELECT document FROM invoices ORDER BY id")
        ]

    def save_analysis(self, invoice_id: str, analysis: DocumentAnalysisResult) -> None:
        self._upsert_document("document_analyses", "invoice_id", invoice_id, analysis)

    def list_analyses(self) -> dict[str, DocumentAnalysisResult]:
        return {
            str(row[0]): self._decode(DocumentAnalysisResult, row[1])  # type: ignore[dict-item]
            for row in self._read_all("SELECT invoice_id, document FROM document_analyses")
        }

    def save_verification(self, verification: Verification) -> None:
        self._upsert_document("verifications", "id", verification.id, verification)

    def list_verifications(self) -> list[Verification]:
        return [
            self._decode(Verification, row[0])  # type: ignore[list-item]
            for row in self._read_all("SELECT document FROM verifications ORDER BY id")
        ]

    def save_agent_run(self, run: AgentRun) -> None:
        self._write(
            lambda cursor: cursor.execute(
                """INSERT INTO agent_runs (id, invoice_id, document) VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET invoice_id = EXCLUDED.invoice_id, document = EXCLUDED.document""",
                (run.id, run.invoice_id, self._encode(run)),
            )
        )

    def get_agent_run(self, run_id: str) -> AgentRun | None:
        row = self._read_one("SELECT document FROM agent_runs WHERE id = %s", (run_id,))
        return self._decode(AgentRun, row[0]) if row else None  # type: ignore[arg-type]

    def list_agent_runs(self, invoice_id: str) -> list[AgentRun]:
        return [self._decode(AgentRun, row[0]) for row in self._read_all(
            "SELECT document FROM agent_runs WHERE invoice_id = %s ORDER BY id", (invoice_id,)
        )]  # type: ignore[list-item]

    def save_agent_tool_call(self, call: AgentToolCall) -> None:
        self._write(
            lambda cursor: cursor.execute(
                """INSERT INTO agent_tool_calls (id, run_id, sequence, document) VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET document = EXCLUDED.document""",
                (call.id, call.run_id, call.sequence, self._encode(call)),
            )
        )

    def list_agent_tool_calls(self, run_id: str) -> list[AgentToolCall]:
        return [self._decode(AgentToolCall, row[0]) for row in self._read_all(
            "SELECT document FROM agent_tool_calls WHERE run_id = %s ORDER BY sequence", (run_id,)
        )]  # type: ignore[list-item]

    def save_agent_handoff(self, handoff: AgentHandoff) -> None:
        self._write(
            lambda cursor: cursor.execute(
                """INSERT INTO agent_handoffs (id, run_id, document) VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET document = EXCLUDED.document""",
                (handoff.id, handoff.run_id, self._encode(handoff)),
            )
        )

    def list_agent_handoffs(self, run_id: str) -> list[AgentHandoff]:
        return [self._decode(AgentHandoff, row[0]) for row in self._read_all(
            "SELECT document FROM agent_handoffs WHERE run_id = %s ORDER BY id", (run_id,)
        )]  # type: ignore[list-item]

    def _upsert_document(self, table: str, key: str, value: str, document: object) -> None:
        self._write(
            lambda cursor: cursor.execute(  # type: ignore[attr-defined]
                f"""
                INSERT INTO {table} ({key}, document) VALUES (%s, %s::jsonb)
                ON CONFLICT ({key}) DO UPDATE SET document = EXCLUDED.document
                """,
                (value, self._encode(document)),
            )
        )
