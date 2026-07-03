"""Backfill materials file bytes that the initial migration skipped.

`migrate_from_neon.py` copied recruitment-document *metadata* only, leaving
``file_data`` and ``blob_url`` NULL (see its step 7). The result: every document
row exists in the new database, but downloading any of them fails because there
are no bytes behind the row. This script closes that gap by copying the actual
file payload from the *source* (legacy Neon) database into the matching target
rows, and re-syncing the external-link rows for good measure.

It is idempotent and safe to re-run: a target document that already has bytes is
left untouched unless ``--force`` is given.

Usage
-----
    # rehearse first — reads source, writes nothing:
    SOURCE_DATABASE_URL="postgresql+psycopg://USER:PW@HOST/db?sslmode=require" \
        uv run python scripts/migrate_materials.py --dry-run

    # then run for real (target defaults to the app's DATABASE_URL / .env):
    SOURCE_DATABASE_URL="postgresql+psycopg://USER:PW@HOST/db?sslmode=require" \
        uv run python scripts/migrate_materials.py

Flags
-----
    --dry-run    Read + report source byte counts, write nothing.
    --force      Overwrite target rows that already have bytes/blob_url.

Notes
-----
* Copies whichever payload the source used: ``file_data`` (Postgres bytea) and/or
  ``blob_url`` (Vercel Blob reference). If the source used Vercel Blob, the
  ``blob_url`` is copied verbatim — the blob itself must remain reachable, or be
  re-hosted separately; this script does not move blob objects between projects.
* Matches rows by primary key, so run AFTER `migrate_from_neon.py` has created
  the document metadata rows.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

# Make `app` importable when run as `python scripts/migrate_materials.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.models import ExternalLink, RecruitmentDocument  # noqa: E402


def _utc(dt: Any) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _rows(src: Session, table: str) -> list[dict[str, Any]]:
    if not inspect(src.bind).has_table(table):
        print(f"  ! source table '{table}' not found — skipping")
        return []
    result = src.execute(text(f'SELECT * FROM "{table}"'))  # noqa: S608 (fixed table name)
    return [dict(m) for m in result.mappings().all()]


def backfill_links(src: Session, dst: Session, *, dry_run: bool) -> int:
    """Ensure every source link exists in the target (metadata is bytes-free)."""
    rows = _rows(src, "external_link")
    created = 0
    for r in rows:
        if dst.get(ExternalLink, r["id"]):
            continue
        created += 1
        if not dry_run:
            dst.add(ExternalLink(
                id=r["id"],
                title=r["title"],
                url=r["url"],
                description=r.get("description"),
                category=r.get("category") or "general",
                is_active=bool(r.get("is_active", True)),
                sort_order=r.get("sort_order") or 0,
                created_at=_utc(r.get("created_at")),
                last_modified=_utc(r.get("last_modified")),
            ))
    print(f"External links: {len(rows)} in source, {created} missing from target"
          f"{' (would insert)' if dry_run else ' (inserted)'}")
    return created


def backfill_document_bytes(src: Session, dst: Session, *, dry_run: bool, force: bool) -> dict[str, int]:
    """Copy file_data / blob_url from source documents into target rows."""
    rows = _rows(src, "recruitment_document")
    stats = {"source": len(rows), "with_payload": 0, "copied": 0, "skipped_present": 0, "missing_target": 0}

    for r in rows:
        file_data = r.get("file_data")
        blob_url = r.get("blob_url")
        if not file_data and not blob_url:
            continue
        stats["with_payload"] += 1

        doc = dst.get(RecruitmentDocument, r["id"])
        if doc is None:
            stats["missing_target"] += 1
            print(f"  ! doc id={r['id']} '{r.get('title')}' not in target — "
                  f"run migrate_from_neon.py first")
            continue
        if (doc.file_data or doc.blob_url) and not force:
            stats["skipped_present"] += 1
            continue

        size = len(file_data) if file_data else 0
        stats["copied"] += 1
        label = f"blob_url" if blob_url else f"{size} bytes"
        print(f"  + doc id={r['id']} '{doc.title}' ({label})")
        if not dry_run:
            doc.file_data = file_data
            doc.blob_url = blob_url

    print(
        f"Documents: {stats['source']} in source, {stats['with_payload']} carry a payload, "
        f"{stats['copied']} {'would be copied' if dry_run else 'copied'}, "
        f"{stats['skipped_present']} already present (use --force to overwrite), "
        f"{stats['missing_target']} missing from target"
    )
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill materials file bytes from the legacy Neon DB.")
    ap.add_argument("--dry-run", action="store_true", help="read + count only, write nothing")
    ap.add_argument("--force", action="store_true", help="overwrite target rows that already have a payload")
    args = ap.parse_args()

    source_url = os.environ.get("SOURCE_DATABASE_URL")
    if not source_url:
        print("ERROR: set SOURCE_DATABASE_URL to the legacy Neon database.", file=sys.stderr)
        return 2
    target_url = settings.database_url

    print(f"Source: {source_url.split('@')[-1]}")
    print(f"Target: {target_url.split('@')[-1]}")
    if args.dry_run:
        print("(dry run — no writes)\n")

    src_engine = create_engine(source_url)
    dst_engine = create_engine(target_url)

    if not inspect(dst_engine).has_table("recruitment_document") and not args.dry_run:
        print("ERROR: target has no 'recruitment_document' table. Run `alembic upgrade head` first.",
              file=sys.stderr)
        return 2

    with Session(src_engine) as src, Session(dst_engine) as dst:
        backfill_links(src, dst, dry_run=args.dry_run)
        stats = backfill_document_bytes(src, dst, dry_run=args.dry_run, force=args.force)
        if not args.dry_run:
            dst.commit()

    print("\nDone.")
    return 0 if stats["missing_target"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
