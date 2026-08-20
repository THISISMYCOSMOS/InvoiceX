from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path


def test_frontend_demo_pricing_fixture_matches_backend() -> None:
    backend = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "scripts/generate_demo_pricing_fixture.py", "--check"],
        cwd=backend,
        check=True,
    )


def test_demo_rebuild_creates_a_backup_and_fresh_schema(tmp_path: Path) -> None:
    backend = Path(__file__).resolve().parents[1]
    database = tmp_path / "demo.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE legacy_record (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO legacy_record VALUES (1)")
    subprocess.run(
        [sys.executable, "scripts/rebuild_demo_data.py", str(database), "--yes"],
        cwd=backend,
        check=True,
    )
    backups = list(tmp_path.glob("demo.backup-*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert "invoices" in tables
    assert "legacy_record" not in tables
