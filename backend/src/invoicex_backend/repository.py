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

from invoicex_backend.agent_activity import AgentHandoff, AgentRun, AgentToolCall
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import OnboardingApiError
from invoicex_backend.models import (
    AgentDecision,
    InvestorMandate,
    Invoice,
    RwaAsset,
    VaultBalance,
    Verification,
)
from invoicex_backend.onboarding_models import (
    Company,
    CompanyWallet,
    LogicalVault,
    OnboardingStatus,
    OnboardingUser,
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
    def get_onboarding_user(self, privy_user_id: str) -> OnboardingUser | None: ...
    def get_onboarding_user_by_email(self, email: str) -> OnboardingUser | None: ...
    def get_user_password_hash(self, privy_user_id: str) -> str | None: ...
    def save_user_password_hash(self, privy_user_id: str, password_hash: str) -> None: ...
    def ensure_onboarding_user(self, user: OnboardingUser) -> OnboardingUser: ...
    def get_company(self, company_id: str) -> Company | None: ...
    def find_company_by_name(self, name: str, company_type: str) -> Company | None: ...
    def get_company_wallet(self, company_id: str) -> CompanyWallet | None: ...
    def get_company_settlement_wallet(self, company_id: str) -> tuple[str, str] | None: ...
    def save_company_settlement_wallet(
        self, company_id: str, wallet_type: str, wallet_address: str
    ) -> None: ...
    def clear_company_settlement_wallet(self, company_id: str) -> None: ...
    def get_company_vault(self, company_id: str) -> LogicalVault | None: ...
    def save_company_profile(
        self, user: OnboardingUser, company: Company
    ) -> tuple[OnboardingUser, Company]: ...
    def update_company_profile(
        self, user: OnboardingUser, company: Company
    ) -> tuple[OnboardingUser, Company]: ...
    def complete_onboarding(
        self,
        privy_user_id: str,
        wallet: CompanyWallet,
        vault: LogicalVault | None,
    ) -> OnboardingUser: ...
    def rotate_wallet_idempotency_key(self, privy_user_id: str, value: str) -> None: ...
    def delete_onboarding_user(self, privy_user_id: str) -> None: ...


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
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    company_type TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    registration_number TEXT NOT NULL,
                    kyb_status TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    privy_user_id TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL,
                    name TEXT,
                    title TEXT,
                    phone TEXT,
                    company_id TEXT UNIQUE REFERENCES companies(id),
                    onboarding_status TEXT NOT NULL,
                    wallet_idempotency_key TEXT,
                    password_hash TEXT
                );
                CREATE TABLE IF NOT EXISTS wallets (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL UNIQUE REFERENCES companies(id),
                    privy_user_id TEXT NOT NULL,
                    wallet_type TEXT NOT NULL,
                    privy_wallet_id TEXT NOT NULL UNIQUE,
                    chain TEXT NOT NULL,
                    address TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS company_settlement_wallets (
                    company_id TEXT PRIMARY KEY REFERENCES companies(id),
                    wallet_type TEXT NOT NULL,
                    wallet_address TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS company_vaults (
                    id TEXT PRIMARY KEY,
                    investor_company_id TEXT NOT NULL UNIQUE REFERENCES companies(id),
                    available_usdc INTEGER NOT NULL CHECK (available_usdc >= 0),
                    status TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS users_normalized_email_unique
                ON users(LOWER(TRIM(email)));
                """
            )
            self._migrate_company_schema()
            self._migrate_user_schema()
            self._connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS companies_country_registration_unique
                ON companies(country_code, registration_number)
                """
            )

    def _migrate_company_schema(self) -> None:
        """Upgrade the local SQLite company identifier without losing demo data."""

        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(companies)").fetchall()
        }
        if "country_code" in columns and "registration_number" in columns:
            return
        if "business_registration_number" not in columns:
            raise RuntimeError("Unsupported companies table schema")

        self._connection.executescript(
            """
            CREATE TABLE companies_v2 (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                company_type TEXT NOT NULL,
                country_code TEXT NOT NULL,
                registration_number TEXT NOT NULL,
                kyb_status TEXT NOT NULL,
                status TEXT NOT NULL
            );
            INSERT INTO companies_v2 (
                id, name, company_type, country_code, registration_number,
                kyb_status, status
            )
            SELECT
                id, name, company_type, 'KR',
                UPPER(REPLACE(REPLACE(business_registration_number, '-', ''), ' ', '')),
                kyb_status, status
            FROM companies;
            DROP TABLE companies;
            ALTER TABLE companies_v2 RENAME TO companies;
            """
        )

    def _migrate_user_schema(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(users)").fetchall()
        }
        if "password_hash" not in columns:
            self._connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

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

    @staticmethod
    def _onboarding_user(row: sqlite3.Row) -> OnboardingUser:
        return OnboardingUser(
            id=row["id"],
            privy_user_id=row["privy_user_id"],
            email=row["email"],
            name=row["name"],
            title=row["title"],
            phone=row["phone"],
            company_id=row["company_id"],
            onboarding_status=OnboardingStatus(row["onboarding_status"]),
            wallet_idempotency_key=row["wallet_idempotency_key"],
        )

    @staticmethod
    def _company(row: sqlite3.Row) -> Company:
        return Company(
            id=row["id"],
            name=row["name"],
            type=row["company_type"],
            country_code=row["country_code"],
            registration_number=row["registration_number"],
            kyb_status=row["kyb_status"],
            status=row["status"],
        )

    @staticmethod
    def _company_wallet(row: sqlite3.Row) -> CompanyWallet:
        return CompanyWallet(
            id=row["id"],
            company_id=row["company_id"],
            privy_user_id=row["privy_user_id"],
            wallet_type=row["wallet_type"],
            privy_wallet_id=row["privy_wallet_id"],
            chain=row["chain"],
            address=row["address"],
            status=row["status"],
        )

    @staticmethod
    def _company_vault(row: sqlite3.Row) -> LogicalVault:
        return LogicalVault(
            id=row["id"],
            investor_company_id=row["investor_company_id"],
            available_usdc=row["available_usdc"],
            status=row["status"],
        )

    def get_onboarding_user(self, privy_user_id: str) -> OnboardingUser | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM users WHERE privy_user_id = ?", (privy_user_id,)
            ).fetchone()
        return self._onboarding_user(row) if row is not None else None

    def get_onboarding_user_by_email(self, email: str) -> OnboardingUser | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))", (email,)
            ).fetchone()
        return self._onboarding_user(row) if row is not None else None

    def get_user_password_hash(self, privy_user_id: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT password_hash FROM users WHERE privy_user_id = ?", (privy_user_id,)
            ).fetchone()
        return str(row["password_hash"]) if row and row["password_hash"] is not None else None

    def save_user_password_hash(self, privy_user_id: str, password_hash: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE users SET password_hash = ? WHERE privy_user_id = ?",
                (password_hash, privy_user_id),
            )

    def ensure_onboarding_user(self, user: OnboardingUser) -> OnboardingUser:
        with self._lock, self._connection:
            existing_email = self._connection.execute(
                "SELECT privy_user_id FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))",
                (user.email,),
            ).fetchone()
            if (
                existing_email is not None
                and existing_email["privy_user_id"] != user.privy_user_id
            ):
                raise OnboardingApiError(
                    409,
                    "EMAIL_ALREADY_REGISTERED",
                    "이미 가입에 사용된 이메일입니다.",
                )
            try:
                self._connection.execute(
                    """
                    INSERT INTO users (
                        id, privy_user_id, email, name, title, phone, company_id,
                        onboarding_status, wallet_idempotency_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(privy_user_id) DO NOTHING
                    """,
                    (
                        user.id,
                        user.privy_user_id,
                        user.email,
                        user.name,
                        user.title,
                        user.phone,
                        user.company_id,
                        user.onboarding_status.value,
                        user.wallet_idempotency_key,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise OnboardingApiError(
                    409,
                    "EMAIL_ALREADY_REGISTERED",
                    "이미 가입에 사용된 이메일입니다.",
                ) from exc
            row = self._connection.execute(
                "SELECT * FROM users WHERE privy_user_id = ?", (user.privy_user_id,)
            ).fetchone()
        assert row is not None
        return self._onboarding_user(row)

    def get_company(self, company_id: str) -> Company | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM companies WHERE id = ?", (company_id,)
            ).fetchone()
        return self._company(row) if row is not None else None

    def find_company_by_name(self, name: str, company_type: str) -> Company | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM companies
                WHERE company_type = ? AND LOWER(TRIM(name)) = LOWER(TRIM(?))
                """,
                (company_type, name),
            ).fetchone()
        return self._company(row) if row is not None else None

    def get_company_wallet(self, company_id: str) -> CompanyWallet | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM wallets WHERE company_id = ?", (company_id,)
            ).fetchone()
        return self._company_wallet(row) if row is not None else None

    def get_company_settlement_wallet(self, company_id: str) -> tuple[str, str] | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT wallet_type, wallet_address
                FROM company_settlement_wallets WHERE company_id = ?
                """,
                (company_id,),
            ).fetchone()
        return (str(row["wallet_type"]), str(row["wallet_address"])) if row else None

    def save_company_settlement_wallet(
        self, company_id: str, wallet_type: str, wallet_address: str
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO company_settlement_wallets (company_id, wallet_type, wallet_address)
                VALUES (?, ?, ?)
                ON CONFLICT(company_id) DO UPDATE SET
                    wallet_type = excluded.wallet_type,
                    wallet_address = excluded.wallet_address
                """,
                (company_id, wallet_type, wallet_address),
            )

    def clear_company_settlement_wallet(self, company_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM company_settlement_wallets WHERE company_id = ?", (company_id,)
            )

    def get_company_vault(self, company_id: str) -> LogicalVault | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM company_vaults WHERE investor_company_id = ?", (company_id,)
            ).fetchone()
        return self._company_vault(row) if row is not None else None

    def save_company_profile(
        self, user: OnboardingUser, company: Company
    ) -> tuple[OnboardingUser, Company]:
        with self._lock, self._connection:
            current_row = self._connection.execute(
                "SELECT * FROM users WHERE privy_user_id = ?", (user.privy_user_id,)
            ).fetchone()
            if current_row is None:
                raise OnboardingApiError(409, "ONBOARDING_STATE_INVALID", "가입 상태가 없습니다.")
            current = self._onboarding_user(current_row)
            if current.onboarding_status is OnboardingStatus.COMPLETED:
                raise OnboardingApiError(
                    409,
                    "ONBOARDING_ALREADY_COMPLETED",
                    "이미 가입이 완료된 Privy 사용자입니다.",
                )
            if current.company_id is not None:
                existing_row = self._connection.execute(
                    "SELECT * FROM companies WHERE id = ?", (current.company_id,)
                ).fetchone()
                if existing_row is None:
                    raise OnboardingApiError(
                        409, "ONBOARDING_STATE_INVALID", "연결된 기업 정보를 찾을 수 없습니다."
                    )
                existing = self._company(existing_row)
                if (
                    existing.name != company.name
                    or existing.type != company.type
                    or existing.country_code != company.country_code
                    or existing.registration_number != company.registration_number
                ):
                    raise OnboardingApiError(
                        409,
                        "ONBOARDING_ALREADY_IN_PROGRESS",
                        "이미 다른 기업 정보로 가입이 진행 중입니다.",
                    )
                if current.onboarding_status is OnboardingStatus.WITHDRAWN:
                    self._connection.execute(
                        """
                        UPDATE users
                        SET name = ?, title = ?, phone = ?,
                            onboarding_status = ?, wallet_idempotency_key = ?
                        WHERE privy_user_id = ?
                        """,
                        (
                            user.name,
                            user.title,
                            user.phone,
                            OnboardingStatus.PROVISIONING_EMBEDDED_WALLET.value,
                            user.wallet_idempotency_key,
                            user.privy_user_id,
                        ),
                    )
                    rejoined_row = self._connection.execute(
                        "SELECT * FROM users WHERE privy_user_id = ?", (user.privy_user_id,)
                    ).fetchone()
                    assert rejoined_row is not None
                    return self._onboarding_user(rejoined_row), existing
                return current, existing
            duplicate = self._connection.execute(
                """
                SELECT id FROM companies
                WHERE country_code = ? AND registration_number = ?
                """,
                (company.country_code, company.registration_number),
            ).fetchone()
            if duplicate is not None:
                raise OnboardingApiError(
                    409,
                    "COMPANY_REGISTRATION_ALREADY_USED",
                    "해당 국가에서 이미 가입에 사용된 기업 등록번호입니다.",
                )
            try:
                self._connection.execute(
                    """
                    INSERT INTO companies (
                        id, name, company_type, country_code, registration_number,
                        kyb_status, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        company.id,
                        company.name,
                        company.type.value,
                        company.country_code,
                        company.registration_number,
                        company.kyb_status,
                        company.status,
                    ),
                )
                self._connection.execute(
                    """
                    UPDATE users
                    SET name = ?, title = ?, phone = ?, company_id = ?,
                        onboarding_status = ?, wallet_idempotency_key = ?
                    WHERE privy_user_id = ?
                    """,
                    (
                        user.name,
                        user.title,
                        user.phone,
                        company.id,
                        OnboardingStatus.PROVISIONING_EMBEDDED_WALLET.value,
                        user.wallet_idempotency_key,
                        user.privy_user_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise OnboardingApiError(
                    409,
                    "COMPANY_REGISTRATION_ALREADY_USED",
                    "해당 국가에서 이미 가입에 사용된 기업 등록번호입니다.",
                ) from exc
            saved_row = self._connection.execute(
                "SELECT * FROM users WHERE privy_user_id = ?", (user.privy_user_id,)
            ).fetchone()
        assert saved_row is not None
        return self._onboarding_user(saved_row), company

    def update_company_profile(
        self, user: OnboardingUser, company: Company
    ) -> tuple[OnboardingUser, Company]:
        with self._lock, self._connection:
            current_user_row = self._connection.execute(
                "SELECT * FROM users WHERE privy_user_id = ?", (user.privy_user_id,)
            ).fetchone()
            if current_user_row is None or self._onboarding_user(current_user_row).company_id != company.id:
                raise OnboardingApiError(
                    409, "COMPANY_PROFILE_NOT_FOUND", "수정할 기업 정보를 찾을 수 없습니다."
                )
            duplicate = self._connection.execute(
                """
                SELECT id FROM companies
                WHERE country_code = ? AND registration_number = ? AND id != ?
                """,
                (company.country_code, company.registration_number, company.id),
            ).fetchone()
            if duplicate is not None:
                raise OnboardingApiError(
                    409,
                    "COMPANY_REGISTRATION_ALREADY_USED",
                    "해당 국가에서 이미 가입에 사용된 기업 등록번호입니다.",
                )
            try:
                self._connection.execute(
                    "UPDATE companies SET name = ?, registration_number = ? WHERE id = ?",
                    (company.name, company.registration_number, company.id),
                )
                self._connection.execute(
                    """
                    UPDATE users SET name = ?, title = ?, phone = ?
                    WHERE privy_user_id = ?
                    """,
                    (user.name, user.title, user.phone, user.privy_user_id),
                )
            except sqlite3.IntegrityError as exc:
                raise OnboardingApiError(
                    409,
                    "COMPANY_REGISTRATION_ALREADY_USED",
                    "해당 국가에서 이미 가입에 사용된 기업 등록번호입니다.",
                ) from exc
        saved_user = self.get_onboarding_user(user.privy_user_id)
        saved_company = self.get_company(company.id)
        assert saved_user is not None and saved_company is not None
        return saved_user, saved_company

    def complete_onboarding(
        self,
        privy_user_id: str,
        wallet: CompanyWallet,
        vault: LogicalVault | None,
    ) -> OnboardingUser:
        with self._lock, self._connection:
            user_row = self._connection.execute(
                "SELECT * FROM users WHERE privy_user_id = ?", (privy_user_id,)
            ).fetchone()
            if user_row is None or user_row["company_id"] != wallet.company_id:
                raise OnboardingApiError(409, "ONBOARDING_STATE_INVALID", "가입 상태가 없습니다.")
            existing_wallet = self._connection.execute(
                "SELECT * FROM wallets WHERE company_id = ?", (wallet.company_id,)
            ).fetchone()
            if existing_wallet is None:
                try:
                    self._connection.execute(
                        """
                        INSERT INTO wallets (
                            id, company_id, privy_user_id, wallet_type, privy_wallet_id,
                            chain, address, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            wallet.id,
                            wallet.company_id,
                            wallet.privy_user_id,
                            wallet.wallet_type,
                            wallet.privy_wallet_id,
                            wallet.chain,
                            wallet.address,
                            wallet.status,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise OnboardingApiError(
                        409,
                        "EMBEDDED_WALLET_ALREADY_LINKED",
                        "해당 Embedded Wallet은 이미 다른 기업에 연결되어 있습니다.",
                    ) from exc
            elif (
                existing_wallet["privy_wallet_id"] != wallet.privy_wallet_id
                or existing_wallet["privy_user_id"] != privy_user_id
            ):
                raise OnboardingApiError(
                    409,
                    "EMBEDDED_WALLET_ALREADY_LINKED",
                    "기업에 다른 Embedded Wallet이 연결되어 있습니다.",
                )
            if vault is not None:
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO company_vaults (
                        id, investor_company_id, available_usdc, status
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (vault.id, vault.investor_company_id, vault.available_usdc, vault.status),
                )
            self._connection.execute(
                """
                UPDATE users
                SET onboarding_status = ?, wallet_idempotency_key = NULL
                WHERE privy_user_id = ?
                """,
                (OnboardingStatus.COMPLETED.value, privy_user_id),
            )
            saved_row = self._connection.execute(
                "SELECT * FROM users WHERE privy_user_id = ?", (privy_user_id,)
            ).fetchone()
        assert saved_row is not None
        return self._onboarding_user(saved_row)

    def rotate_wallet_idempotency_key(self, privy_user_id: str, value: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                UPDATE users SET wallet_idempotency_key = ?
                WHERE privy_user_id = ? AND onboarding_status = ?
                """,
                (
                    value,
                    privy_user_id,
                    OnboardingStatus.PROVISIONING_EMBEDDED_WALLET.value,
                ),
            )

    def delete_onboarding_user(self, privy_user_id: str) -> None:
        with self._lock, self._connection:
            user_row = self._connection.execute(
                "SELECT company_id FROM users WHERE privy_user_id = ?", (privy_user_id,)
            ).fetchone()
            if user_row is None:
                return
            company_id = user_row["company_id"]
            if company_id is not None:
                self._connection.execute(
                    "DELETE FROM company_settlement_wallets WHERE company_id = ?", (company_id,)
                )
                self._connection.execute(
                    "DELETE FROM company_vaults WHERE investor_company_id = ?", (company_id,)
                )
                self._connection.execute(
                    "DELETE FROM wallets WHERE company_id = ?", (company_id,)
                )
            self._connection.execute(
                "DELETE FROM users WHERE privy_user_id = ?", (privy_user_id,)
            )
            if company_id is not None:
                self._connection.execute("DELETE FROM companies WHERE id = ?", (company_id,))


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
        """
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company_type TEXT NOT NULL,
            business_registration_number TEXT NOT NULL UNIQUE,
            kyb_status TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            privy_user_id TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            name TEXT,
            title TEXT,
            phone TEXT,
            company_id TEXT UNIQUE REFERENCES companies(id),
            onboarding_status TEXT NOT NULL,
            wallet_idempotency_key TEXT,
            password_hash TEXT
        )
        """,
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT",
        """
        CREATE TABLE IF NOT EXISTS wallets (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL UNIQUE REFERENCES companies(id),
            privy_user_id TEXT NOT NULL,
            wallet_type TEXT NOT NULL,
            privy_wallet_id TEXT NOT NULL UNIQUE,
            chain TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS company_settlement_wallets (
            company_id TEXT PRIMARY KEY REFERENCES companies(id),
            wallet_type TEXT NOT NULL,
            wallet_address TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS company_vaults (
            id TEXT PRIMARY KEY,
            investor_company_id TEXT NOT NULL UNIQUE REFERENCES companies(id),
            available_usdc BIGINT NOT NULL CHECK (available_usdc >= 0),
            status TEXT NOT NULL
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

    @staticmethod
    def _onboarding_user(row: tuple[object, ...]) -> OnboardingUser:
        return OnboardingUser(
            id=str(row[0]),
            privy_user_id=str(row[1]),
            email=str(row[2]),
            name=str(row[3]) if row[3] is not None else None,
            title=str(row[4]) if row[4] is not None else None,
            phone=str(row[5]) if row[5] is not None else None,
            company_id=str(row[6]) if row[6] is not None else None,
            onboarding_status=OnboardingStatus(str(row[7])),
            wallet_idempotency_key=str(row[8]) if row[8] is not None else None,
        )

    @staticmethod
    def _company(row: tuple[object, ...]) -> Company:
        return Company(
            id=str(row[0]),
            name=str(row[1]),
            type=str(row[2]),
            country_code="KR",
            registration_number=str(row[3]),
            kyb_status=str(row[4]),
            status=str(row[5]),
        )

    def get_onboarding_user(self, privy_user_id: str) -> OnboardingUser | None:
        row = self._read_one(
            """
            SELECT id, privy_user_id, email, name, title, phone, company_id,
                   onboarding_status, wallet_idempotency_key
            FROM users WHERE privy_user_id = %s
            """,
            (privy_user_id,),
        )
        return self._onboarding_user(row) if row else None

    def get_onboarding_user_by_email(self, email: str) -> OnboardingUser | None:
        row = self._read_one(
            """
            SELECT id, privy_user_id, email, name, title, phone, company_id,
                   onboarding_status, wallet_idempotency_key
            FROM users WHERE LOWER(BTRIM(email)) = LOWER(BTRIM(%s))
            """,
            (email,),
        )
        return self._onboarding_user(row) if row else None

    def get_user_password_hash(self, privy_user_id: str) -> str | None:
        row = self._read_one(
            "SELECT password_hash FROM users WHERE privy_user_id = %s",
            (privy_user_id,),
        )
        return str(row[0]) if row and row[0] is not None else None

    def save_user_password_hash(self, privy_user_id: str, password_hash: str) -> None:
        self._write(
            lambda cursor: cursor.execute(  # type: ignore[attr-defined]
                "UPDATE users SET password_hash = %s WHERE privy_user_id = %s",
                (password_hash, privy_user_id),
            )
        )

    def ensure_onboarding_user(self, user: OnboardingUser) -> OnboardingUser:
        self._write(
            lambda cursor: cursor.execute(
                """
                INSERT INTO users (
                    id, privy_user_id, email, name, title, phone, company_id,
                    onboarding_status, wallet_idempotency_key
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (privy_user_id) DO NOTHING
                """,
                (
                    user.id,
                    user.privy_user_id,
                    user.email,
                    user.name,
                    user.title,
                    user.phone,
                    user.company_id,
                    user.onboarding_status.value,
                    user.wallet_idempotency_key,
                ),
            )
        )
        saved = self.get_onboarding_user(user.privy_user_id)
        assert saved is not None
        return saved

    def get_company(self, company_id: str) -> Company | None:
        row = self._read_one(
            """
            SELECT id, name, company_type, business_registration_number, kyb_status, status
            FROM companies WHERE id = %s
            """,
            (company_id,),
        )
        return self._company(row) if row else None

    def find_company_by_name(self, name: str, company_type: str) -> Company | None:
        row = self._read_one(
            """
            SELECT id, name, company_type, business_registration_number, kyb_status, status
            FROM companies
            WHERE company_type = %s AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
            """,
            (company_type, name),
        )
        return self._company(row) if row else None

    def get_company_wallet(self, company_id: str) -> CompanyWallet | None:
        row = self._read_one(
            """
            SELECT id, company_id, privy_user_id, wallet_type, privy_wallet_id,
                   chain, address, status
            FROM wallets WHERE company_id = %s
            """,
            (company_id,),
        )
        if row is None:
            return None
        return CompanyWallet(
            id=str(row[0]),
            company_id=str(row[1]),
            privy_user_id=str(row[2]),
            wallet_type=str(row[3]),
            privy_wallet_id=str(row[4]),
            chain=str(row[5]),
            address=str(row[6]),
            status=str(row[7]),
        )

    def get_company_settlement_wallet(self, company_id: str) -> tuple[str, str] | None:
        row = self._read_one(
            """
            SELECT wallet_type, wallet_address
            FROM company_settlement_wallets WHERE company_id = %s
            """,
            (company_id,),
        )
        return (str(row[0]), str(row[1])) if row else None

    def save_company_settlement_wallet(
        self, company_id: str, wallet_type: str, wallet_address: str
    ) -> None:
        self._write(
            lambda cursor: cursor.execute(  # type: ignore[attr-defined]
                """
                INSERT INTO company_settlement_wallets (company_id, wallet_type, wallet_address)
                VALUES (%s, %s, %s)
                ON CONFLICT (company_id) DO UPDATE SET
                    wallet_type = EXCLUDED.wallet_type,
                    wallet_address = EXCLUDED.wallet_address
                """,
                (company_id, wallet_type, wallet_address),
            )
        )

    def clear_company_settlement_wallet(self, company_id: str) -> None:
        self._write(
            lambda cursor: cursor.execute(  # type: ignore[attr-defined]
                "DELETE FROM company_settlement_wallets WHERE company_id = %s", (company_id,)
            )
        )

    def get_company_vault(self, company_id: str) -> LogicalVault | None:
        row = self._read_one(
            """
            SELECT id, investor_company_id, available_usdc, status
            FROM company_vaults WHERE investor_company_id = %s
            """,
            (company_id,),
        )
        if row is None:
            return None
        return LogicalVault(
            id=str(row[0]),
            investor_company_id=str(row[1]),
            available_usdc=int(row[2]),
            status=str(row[3]),
        )

    def save_company_profile(
        self, user: OnboardingUser, company: Company
    ) -> tuple[OnboardingUser, Company]:
        current = self.get_onboarding_user(user.privy_user_id)
        if current is None:
            raise OnboardingApiError(409, "ONBOARDING_STATE_INVALID", "가입 상태가 없습니다.")
        if current.onboarding_status is OnboardingStatus.COMPLETED:
            raise OnboardingApiError(
                409,
                "ONBOARDING_ALREADY_COMPLETED",
                "이미 가입이 완료된 Privy 사용자입니다.",
            )
        if current.company_id is not None:
            existing = self.get_company(current.company_id)
            if existing is None:
                raise OnboardingApiError(
                    409, "ONBOARDING_STATE_INVALID", "연결된 기업 정보를 찾을 수 없습니다."
                )
            if (
                existing.name != company.name
                or existing.type != company.type
                or existing.registration_number != company.registration_number
            ):
                raise OnboardingApiError(
                    409,
                    "ONBOARDING_ALREADY_IN_PROGRESS",
                    "이미 다른 기업 정보로 가입이 진행 중입니다.",
                )
            if current.onboarding_status is OnboardingStatus.WITHDRAWN:
                def reactivate(cursor: object) -> None:
                    cursor.execute(  # type: ignore[attr-defined]
                        """
                        UPDATE users
                        SET name = %s, title = %s, phone = %s,
                            onboarding_status = %s, wallet_idempotency_key = %s
                        WHERE privy_user_id = %s
                        """,
                        (
                            user.name,
                            user.title,
                            user.phone,
                            OnboardingStatus.PROVISIONING_EMBEDDED_WALLET.value,
                            user.wallet_idempotency_key,
                            user.privy_user_id,
                        ),
                    )

                self._write(reactivate)
                saved = self.get_onboarding_user(user.privy_user_id)
                assert saved is not None
                return saved, existing
            return current, existing
        duplicate = self._read_one(
            "SELECT id FROM companies WHERE business_registration_number = %s",
            (company.registration_number,),
        )
        if duplicate is not None:
            raise OnboardingApiError(
                409,
                "COMPANY_REGISTRATION_ALREADY_USED",
                "해당 국가에서 이미 가입에 사용된 기업 등록번호입니다.",
            )

        def write(cursor: object) -> None:
            cursor.execute(  # type: ignore[attr-defined]
                """
                INSERT INTO companies (
                    id, name, company_type, business_registration_number, kyb_status, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    company.id,
                    company.name,
                    company.type.value,
                    company.registration_number,
                    company.kyb_status,
                    company.status,
                ),
            )
            cursor.execute(  # type: ignore[attr-defined]
                """
                UPDATE users
                SET name = %s, title = %s, phone = %s, company_id = %s,
                    onboarding_status = %s, wallet_idempotency_key = %s
                WHERE privy_user_id = %s
                """,
                (
                    user.name,
                    user.title,
                    user.phone,
                    company.id,
                    OnboardingStatus.PROVISIONING_EMBEDDED_WALLET.value,
                    user.wallet_idempotency_key,
                    user.privy_user_id,
                ),
            )

        try:
            self._write(write)
        except Exception as exc:
            duplicate = self._read_one(
                "SELECT id FROM companies WHERE business_registration_number = %s",
                (company.registration_number,),
            )
            if duplicate is not None:
                raise OnboardingApiError(
                    409,
                    "COMPANY_REGISTRATION_ALREADY_USED",
                    "해당 국가에서 이미 가입에 사용된 기업 등록번호입니다.",
                ) from exc
            raise
        saved = self.get_onboarding_user(user.privy_user_id)
        assert saved is not None
        return saved, company

    def update_company_profile(
        self, user: OnboardingUser, company: Company
    ) -> tuple[OnboardingUser, Company]:
        current = self.get_onboarding_user(user.privy_user_id)
        if current is None or current.company_id != company.id:
            raise OnboardingApiError(
                409, "COMPANY_PROFILE_NOT_FOUND", "수정할 기업 정보를 찾을 수 없습니다."
            )
        duplicate = self._read_one(
            """
            SELECT id FROM companies
            WHERE business_registration_number = %s AND id != %s
            """,
            (company.registration_number, company.id),
        )
        if duplicate is not None:
            raise OnboardingApiError(
                409,
                "COMPANY_REGISTRATION_ALREADY_USED",
                "이미 가입에 사용된 기업 등록번호입니다.",
            )

        def write(cursor: object) -> None:
            cursor.execute(  # type: ignore[attr-defined]
                """
                UPDATE companies
                SET name = %s, business_registration_number = %s
                WHERE id = %s
                """,
                (company.name, company.registration_number, company.id),
            )
            cursor.execute(  # type: ignore[attr-defined]
                """
                UPDATE users SET name = %s, title = %s, phone = %s
                WHERE privy_user_id = %s
                """,
                (user.name, user.title, user.phone, user.privy_user_id),
            )

        try:
            self._write(write)
        except Exception as exc:
            duplicate = self._read_one(
                """
                SELECT id FROM companies
                WHERE business_registration_number = %s AND id != %s
                """,
                (company.registration_number, company.id),
            )
            if duplicate is not None:
                raise OnboardingApiError(
                    409,
                    "COMPANY_REGISTRATION_ALREADY_USED",
                    "이미 가입에 사용된 기업 등록번호입니다.",
                ) from exc
            raise
        saved_user = self.get_onboarding_user(user.privy_user_id)
        saved_company = self.get_company(company.id)
        assert saved_user is not None and saved_company is not None
        return saved_user, saved_company

    def complete_onboarding(
        self,
        privy_user_id: str,
        wallet: CompanyWallet,
        vault: LogicalVault | None,
    ) -> OnboardingUser:
        user = self.get_onboarding_user(privy_user_id)
        if user is None or user.company_id != wallet.company_id:
            raise OnboardingApiError(409, "ONBOARDING_STATE_INVALID", "가입 상태가 없습니다.")
        existing_wallet = self.get_company_wallet(wallet.company_id)
        if existing_wallet is not None and (
            existing_wallet.privy_wallet_id != wallet.privy_wallet_id
            or existing_wallet.privy_user_id != privy_user_id
        ):
            raise OnboardingApiError(
                409,
                "EMBEDDED_WALLET_ALREADY_LINKED",
                "기업에 다른 Embedded Wallet이 연결되어 있습니다.",
            )

        def write(cursor: object) -> None:
            if existing_wallet is None:
                cursor.execute(  # type: ignore[attr-defined]
                    """
                    INSERT INTO wallets (
                        id, company_id, privy_user_id, wallet_type, privy_wallet_id,
                        chain, address, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        wallet.id,
                        wallet.company_id,
                        wallet.privy_user_id,
                        wallet.wallet_type,
                        wallet.privy_wallet_id,
                        wallet.chain,
                        wallet.address,
                        wallet.status,
                    ),
                )
            if vault is not None:
                cursor.execute(  # type: ignore[attr-defined]
                    """
                    INSERT INTO company_vaults (
                        id, investor_company_id, available_usdc, status
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (investor_company_id) DO NOTHING
                    """,
                    (vault.id, vault.investor_company_id, vault.available_usdc, vault.status),
                )
            cursor.execute(  # type: ignore[attr-defined]
                """
                UPDATE users SET onboarding_status = %s, wallet_idempotency_key = NULL
                WHERE privy_user_id = %s
                """,
                (OnboardingStatus.COMPLETED.value, privy_user_id),
            )

        try:
            self._write(write)
        except Exception as exc:
            raise OnboardingApiError(
                409,
                "EMBEDDED_WALLET_ALREADY_LINKED",
                "해당 Embedded Wallet은 이미 다른 기업에 연결되어 있습니다.",
            ) from exc
        linked = self.get_company_wallet(wallet.company_id)
        if (
            linked is None
            or linked.privy_wallet_id != wallet.privy_wallet_id
            or linked.privy_user_id != privy_user_id
        ):
            raise OnboardingApiError(
                409,
                "EMBEDDED_WALLET_ALREADY_LINKED",
                "기업에 다른 Embedded Wallet이 연결되어 있습니다.",
            )
        saved = self.get_onboarding_user(privy_user_id)
        assert saved is not None
        return saved

    def rotate_wallet_idempotency_key(self, privy_user_id: str, value: str) -> None:
        self._write(
            lambda cursor: cursor.execute(
                """
                UPDATE users SET wallet_idempotency_key = %s
                WHERE privy_user_id = %s AND onboarding_status = %s
                """,
                (
                    value,
                    privy_user_id,
                    OnboardingStatus.PROVISIONING_EMBEDDED_WALLET.value,
                ),
            )
        )

    def delete_onboarding_user(self, privy_user_id: str) -> None:
        current = self.get_onboarding_user(privy_user_id)
        if current is None:
            return

        def delete(cursor: object) -> None:
            if current.company_id is not None:
                cursor.execute(  # type: ignore[attr-defined]
                    "DELETE FROM company_settlement_wallets WHERE company_id = %s",
                    (current.company_id,),
                )
                cursor.execute(  # type: ignore[attr-defined]
                    "DELETE FROM company_vaults WHERE investor_company_id = %s",
                    (current.company_id,),
                )
                cursor.execute(  # type: ignore[attr-defined]
                    "DELETE FROM wallets WHERE company_id = %s",
                    (current.company_id,),
                )
            cursor.execute(  # type: ignore[attr-defined]
                "DELETE FROM users WHERE privy_user_id = %s", (privy_user_id,)
            )
            if current.company_id is not None:
                cursor.execute(  # type: ignore[attr-defined]
                    "DELETE FROM companies WHERE id = %s", (current.company_id,)
                )

        self._write(delete)

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
