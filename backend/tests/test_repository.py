from __future__ import annotations

from invoicex_backend.models import InvestorMandate, MandatePolicy
from invoicex_backend.repository import CloudSqlRwaRepository, SQLiteRwaRepository


class _SchemaCursor:
    def __init__(self, connection: "_SchemaConnection") -> None:
        self.connection = connection
        self.result: list[tuple[object, ...]] = []

    def execute(self, query: str, _params: tuple[object, ...] = ()) -> None:
        self.connection.queries.append(query)
        if "information_schema.tables" in query:
            self.result = [(name,) for name in self.connection.tables]
        elif "information_schema.columns" in query:
            self.result = [(1,)] if self.connection.has_password_hash else []
        else:
            self.result = []

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.result

    def fetchone(self) -> tuple[object, ...] | None:
        return self.result[0] if self.result else None

    def close(self) -> None:
        pass


class _SchemaConnection:
    def __init__(self) -> None:
        self.autocommit = False
        self.tables = set(CloudSqlRwaRepository._required_schema_tables)
        self.has_password_hash = True
        self.queries: list[str] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> _SchemaCursor:
        return _SchemaCursor(self)

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_cloud_sql_skips_startup_ddl_when_schema_is_current() -> None:
    connection = _SchemaConnection()

    repository = CloudSqlRwaRepository(connection)

    assert connection.autocommit is False
    assert len(connection.queries) == 2
    assert all("CREATE TABLE" not in query for query in connection.queries)
    assert connection.commits == 1
    assert connection.rollbacks == 0
    repository.close()
    assert connection.closed is True


def test_new_mandate_replaces_the_previous_active_mandate_for_one_wallet(tmp_path) -> None:
    repository = SQLiteRwaRepository(tmp_path / "rwa.sqlite3")
    policy = MandatePolicy(
        total_investment_limit_usdc=5,
        per_invoice_limit_usdc=1,
        buyer_allowlist=["Prime Mobility"],
        minimum_risk_score=80,
        maximum_remaining_term_days=120,
        expires_at="2030-12-31",
    )
    first = InvestorMandate(
        id="MAN-first",
        owner_wallet_address="wallet-address",
        vault_address="vault-address",
        policy=policy,
        canonical_message="first",
        signature="signature",
        created_at="2026-08-02T00:00:00Z",
    )
    second = first.model_copy(
        update={
            "id": "MAN-second",
            "canonical_message": "second",
            "created_at": "2026-08-02T00:01:00Z",
        }
    )

    repository.save_mandate(first)
    repository.save_mandate(second)

    assert [mandate.id for mandate in repository.active_mandates()] == ["MAN-second"]
    repository.close()
