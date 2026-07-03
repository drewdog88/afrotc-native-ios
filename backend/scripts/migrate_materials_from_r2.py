"""Materials-only migration: Vercel Blob + legacy Neon -> new app Neon.

The legacy Flask app's document *metadata* lived in Neon (`recruitment_document`)
and the file bytes ended up in Vercel Blob (public `*.blob.vercel-storage.com`
URLs). The old R2 `blob_url`s in Neon are stale (those objects were deleted). The
new FastAPI app serves documents from Postgres `file_data` (bytea), so this
script:

  1. lists the surviving documents in Vercel Blob (prefix `documents/`),
  2. downloads each file's bytes from its public URL,
  3. enriches title/category/description from the legacy Neon rows by title match,
  4. inserts documents (WITH file_data) + external links into the TARGET Neon.

Materials-only and additive: never touches recruits/cadets/users. Documents get
fresh target ids (nothing FKs to them); links preserve their source ids. Run
`--dry-run` first — it fetches every byte and reports, writing nothing.

Credentials are read from env files and never printed (only hosts/counts logged):
  --source-env FILE   legacy Neon DATABASE_URL (+ SQLALCHEMY_DATABASE_URI fallback)
  --blob-env FILE     env file with BLOB_READ_WRITE_TOKEN (original Vercel project)
  target              = app settings.database_url (.env)

Usage:
  uv run --with boto3 python scripts/migrate_materials_from_r2.py \
      --source-env legacy.env --blob-env orig.env --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.models import ExternalLink, RecruitmentDocument  # noqa: E402

_BLOB_LIST_API = "https://blob.vercel-storage.com"


def _load_env(path: str, keys: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in keys and v:
            out[k] = v
    return out


def _normalize_pg(url: str) -> str:
    return re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", url)


def _utc(dt: Any) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _norm(s: str) -> str:
    """Normalize a title for fuzzy matching: lowercase alnum tokens only."""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _title_from_pathname(pathname: str) -> str:
    base = pathname.split("/")[-1]
    base = re.sub(r"\.[A-Za-z0-9]+$", "", base)      # drop extension
    base = re.sub(r"^[0-9a-f]{16,}_", "", base)       # drop "<hash>_" prefix
    base = re.sub(r"-[A-Za-z0-9]{10,}$", "", base)    # drop "-<random>" suffix
    return base.replace("_", " ").strip()


_EXT_MIME = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _secure_filename(name: str) -> str:
    return os.path.basename(name).replace("..", "").replace("/", "_").replace("\\", "_") or "unnamed"


def _list_blob_documents(token: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        f"{_BLOB_LIST_API}/?prefix=documents/&limit=1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return [b for b in data.get("blobs", []) if not b["pathname"].endswith("/")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-env", required=True, help="legacy Neon DATABASE_URL env file")
    ap.add_argument("--blob-env", required=True, help="env file with BLOB_READ_WRITE_TOKEN")
    ap.add_argument("--dry-run", action="store_true", help="fetch + report, write nothing")
    args = ap.parse_args()

    src_env = _load_env(args.source_env, {"DATABASE_URL", "SQLALCHEMY_DATABASE_URI"})
    source_url = os.environ.get("SOURCE_DATABASE_URL") or src_env.get("DATABASE_URL") \
        or src_env.get("SQLALCHEMY_DATABASE_URI")
    if not source_url:
        print("ERROR: no legacy DATABASE_URL found", file=sys.stderr)
        return 2
    source_url = _normalize_pg(source_url)
    target_url = settings.database_url

    token = _load_env(args.blob_env, {"BLOB_READ_WRITE_TOKEN"}).get("BLOB_READ_WRITE_TOKEN")
    if not token:
        print("ERROR: BLOB_READ_WRITE_TOKEN not found", file=sys.stderr)
        return 2

    print(f"Source (legacy): {source_url.split('@')[-1]}")
    print(f"Target (app):    {target_url.split('@')[-1]}")
    if args.dry_run:
        print("(dry run — no target writes)")

    # Legacy metadata (for title-matched enrichment) + links (migrated as-is).
    src_engine = create_engine(source_url)
    with Session(src_engine) as src:
        legacy_docs = [dict(m) for m in src.execute(
            text('SELECT * FROM "recruitment_document" ORDER BY id')).mappings()]
        links = [dict(m) for m in src.execute(
            text('SELECT * FROM "external_link" ORDER BY id')).mappings()]
    legacy_by_norm = {_norm(d["title"]): d for d in legacy_docs}

    def _match_legacy(title: str) -> dict | None:
        n = _norm(title)
        if n in legacy_by_norm:
            return legacy_by_norm[n]
        # Fall back to token-subset match (e.g. "afrotc cadet handbook" ~ "cadet
        # handbook", "... hssp applicant guide signed" ~ "hssp applicant guide").
        toks = set(n.split())
        best = None
        for d in legacy_docs:
            lt = set(_norm(d["title"]).split())
            if lt and (lt <= toks or toks <= lt):
                if best is None or len(lt & toks) > len(set(_norm(best["title"]).split()) & toks):
                    best = d
        return best

    blobs = _list_blob_documents(token)
    print(f"\nVercel Blob: {len(blobs)} documents under documents/")
    print(f"Legacy Neon: {len(legacy_docs)} doc rows, {len(links)} links")

    # Download each blob's bytes from its public URL; enrich from legacy by title.
    prepared: list[dict[str, Any]] = []
    print("\nFetching document bytes from Vercel Blob:")
    for b in blobs:
        title = _title_from_pathname(b["pathname"])
        try:
            with urllib.request.urlopen(b["url"], timeout=60) as resp:
                data = resp.read()
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {title}: FAILED ({type(e).__name__})")
            continue
        legacy = _match_legacy(title)
        ext = (b["pathname"].rsplit(".", 1)[-1] or "").lower()
        orig = f"{title}.{ext}" if ext else title
        prepared.append({
            "title": (legacy or {}).get("title") or title,
            "description": (legacy or {}).get("description"),
            "filename": _secure_filename(orig),
            "original_filename": orig,
            "file_size": len(data),
            "file_type": _EXT_MIME.get(ext, "application/octet-stream"),
            "category": (legacy or {}).get("category") or "general",
            "is_active": bool((legacy or {}).get("is_active", True)),
            "sort_order": (legacy or {}).get("sort_order") or 0,
            "created_at": _utc((legacy or {}).get("created_at")),
            "last_modified": _utc((legacy or {}).get("last_modified")),
            "data": data,
        })
        tag = "matched" if legacy else "new"
        print(f"  ✓ {len(data):>9,} B  [{tag:>7}]  {title}")

    unmatched_legacy = [d["title"] for d in legacy_docs
                        if _norm(d["title"]) not in {_norm(p["title"]) for p in prepared}]
    print(f"\nPrepared {len(prepared)} documents "
          f"({sum(len(p['data']) for p in prepared):,} bytes total).")
    if unmatched_legacy:
        print("Legacy docs with NO surviving file (skipped): "
              + ", ".join(unmatched_legacy))

    if args.dry_run:
        print("\nDry run complete — nothing written.")
        return 0

    # Write to target. Documents get fresh ids (no FK dependents). Links preserve
    # source ids, idempotently (skip ids already present).
    dst_engine = create_engine(target_url)
    with Session(dst_engine) as dst:
        have_link_ids = set(dst.scalars(select(ExternalLink.id)).all())
        have_doc_titles = {_norm(t) for t in dst.scalars(select(RecruitmentDocument.title)).all()}

        added_links = 0
        for lk in links:
            if lk["id"] in have_link_ids:
                continue
            dst.add(ExternalLink(
                id=lk["id"], title=lk["title"], url=lk["url"],
                description=lk.get("description"),
                category=lk.get("category") or "general",
                is_active=bool(lk.get("is_active", True)),
                sort_order=lk.get("sort_order") or 0,
                created_at=_utc(lk.get("created_at")),
                last_modified=_utc(lk.get("last_modified")),
            ))
            added_links += 1

        added_docs = 0
        for p in prepared:
            if _norm(p["title"]) in have_doc_titles:
                continue
            data = p.pop("data")
            dst.add(RecruitmentDocument(blob_url=None, file_data=data, **p))
            added_docs += 1
        dst.flush()

        if inspect(dst_engine).dialect.name == "postgresql":
            dst.execute(text(
                "SELECT setval(pg_get_serial_sequence('external_link', 'id'), "
                "COALESCE((SELECT MAX(id) FROM external_link), 1))"))
        dst.commit()

        n_docs = dst.scalar(select(func.count()).select_from(RecruitmentDocument))
        n_bytes = dst.scalar(select(func.count()).select_from(RecruitmentDocument)
                             .where(RecruitmentDocument.file_data.isnot(None)))
        n_links = dst.scalar(select(func.count()).select_from(ExternalLink))
    print(f"\nInserted {added_docs} documents, {added_links} links.")
    print(f"Target now: {n_docs} documents ({n_bytes} with bytes), {n_links} links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
