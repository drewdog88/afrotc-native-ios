"""Detect schema drift: is the live DB's applied Alembic revision behind the repo?

Vercel ships code only and never runs Alembic (see the Deployment wiki page), so
a deploy that adds a migration leaves the production DB a revision behind until
someone runs ``alembic upgrade head`` by hand. That gap is silent until a request
first touches the new table/column and 500s (``UndefinedTable``). This script
makes the gap loud: it compares the repo's migration head(s) against the
revision(s) recorded in the target DB's ``alembic_version`` table.

Read-only — it never writes to the database.

Exit codes (so CI can branch on them):
  0  in sync         — DB is at the repo head(s)
  3  DRIFT           — DB is behind/ahead of the repo head(s)
  2  error           — could not determine state (bad URL, connect failure, …)

Usage:
  DATABASE_URL='postgresql+psycopg://USER:PW@HOST/neondb?sslmode=require' \
    uv run python scripts/check_migration_drift.py

The URL scheme is normalized to the ``postgresql+psycopg`` driver automatically,
so a plain ``postgres://`` / ``postgresql://`` connection string also works.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

BACKEND = Path(__file__).resolve().parents[1]


def _normalize(url: str) -> str:
    """Force the psycopg (v3) driver; leave host/params untouched."""
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def main() -> int:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        print("::error::DATABASE_URL is not set — cannot check migration drift.")
        return 2

    # Repo head(s) — read straight from the versions directory; no env.py, no DB.
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    heads = set(ScriptDirectory.from_config(cfg).get_heads())

    # DB's applied revision(s) — the contents of alembic_version.
    try:
        engine = create_engine(_normalize(raw))
        with engine.connect() as conn:
            current = set(MigrationContext.configure(conn).get_current_heads())
    except Exception as exc:  # noqa: BLE001 — any failure here is an alert-worthy error
        print(f"::error::Could not read the DB migration state: {exc}")
        return 2

    print(f"repo head(s): {sorted(heads) or ['(none)']}")
    print(f"DB revision(s): {sorted(current) or ['(none — alembic_version empty/absent)']}")

    if current == heads:
        print("✅ In sync — the database is at the repo head.")
        return 0

    missing = sorted(heads - current)
    print("🔴 SCHEMA DRIFT — the database is NOT at the repo head.")
    if missing:
        print(f"   Unapplied in DB: {missing}")
    print(
        "   Fix: run migrations against the DIRECT (non-pooled) Neon host —\n"
        "     cd backend && DATABASE_URL='postgresql+psycopg://…@HOST/neondb?sslmode=require' \\\n"
        "       uv run alembic upgrade head\n"
        "   See the Deployment wiki page."
    )
    return 3


if __name__ == "__main__":
    sys.exit(main())
