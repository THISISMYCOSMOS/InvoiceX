#!/usr/bin/env python3
"""Back up and rebuild only the local InvoiceX SQLite demo database."""

from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path

from invoicex_backend.repository import SQLiteRwaRepository


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Back up a local SQLite demo DB, then recreate the current schema."
    )
    parser.add_argument("database", type=Path)
    parser.add_argument("--yes", action="store_true", help="confirm the rebuild")
    args = parser.parse_args()
    database = args.database.expanduser().resolve()
    if database.suffix not in {".sqlite", ".sqlite3", ".db"}:
        raise SystemExit("refusing to rebuild a path that is not a SQLite database")
    if not args.yes:
        raise SystemExit("re-run with --yes after verifying the exact database path")

    backup: Path | None = None
    if database.exists():
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = database.with_name(
            f"{database.stem}.backup-{timestamp}{database.suffix}"
        )
        shutil.copy2(database, backup)
        database.unlink()

    repository = SQLiteRwaRepository(database)
    repository.close()
    print(f"rebuilt: {database}")
    if backup is not None:
        print(f"backup: {backup}")
    print("existing Devnet mints and chain transactions were not modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
