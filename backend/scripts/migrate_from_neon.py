"""One-time data migration: old Flask/Neon schema -> new FastAPI schema.

Reads every row from the *source* database (the existing Neon Postgres that
backed the Flask app) and loads it into the *target* database (the new schema,
created by `alembic upgrade head`). Field shapes are near-identical; the only
real transform is the old free-text ``PotentialRecruit.status`` -> the new
``stage`` enum, plus seeding one baseline ``RecruitStageEvent`` per recruit so
the funnel/trend analytics have history from day one.

Usage
-----
    # target defaults to the app's DATABASE_URL (.env); override if needed.
    SOURCE_DATABASE_URL="postgresql+psycopg://USER:PW@HOST/db?sslmode=require" \
    DATABASE_URL="postgresql+psycopg://.../new_db" \
        uv run python scripts/migrate_from_neon.py

    # rehearse against local SQLite first (safe, no writes to Neon):
    SOURCE_DATABASE_URL="sqlite:///./old_dump.db" \
    DATABASE_URL="sqlite:///./afrotc695.db" \
        uv run python scripts/migrate_from_neon.py --wipe

Flags
-----
    --wipe       Delete existing rows in the target tables before loading.
    --dry-run    Read + report source counts, write nothing.

Notes
-----
* Primary keys are preserved so foreign keys line up. On Postgres the identity
  sequences are re-synced afterward so new inserts don't collide.
* 2FA is intentionally reset on migration (secrets cleared, ``totp_enabled``
  false): the old secrets were stored plaintext-despite-comment, and the new
  system stores them Fernet-encrypted. Users simply re-enroll. Nobody is
  actively using the app, so this is the clean, correct choice.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session

# Make `app` importable when run as `python scripts/migrate_from_neon.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.models import (  # noqa: E402
    ActivityLog,
    Cadet,
    ExternalLink,
    PasswordHistory,
    PotentialRecruit,
    RecruitmentDocument,
    RecruitmentEvent,
    RecruitStageEvent,
    UniversityContact,
    User,
)
from app.models.enums import RecruitStage  # noqa: E402

# Old free-text status -> new funnel stage. Unknown/blank -> LEAD.
_STATUS_TO_STAGE = {
    "prospective": RecruitStage.LEAD,
    "prospect": RecruitStage.LEAD,
    "lead": RecruitStage.LEAD,
    "new": RecruitStage.LEAD,
    "contacted": RecruitStage.CONTACTED,
    "interested": RecruitStage.CONTACTED,
    "in_progress": RecruitStage.CONTACTED,
    "applied": RecruitStage.APPLIED,
    "application": RecruitStage.APPLIED,
    "enrolled": RecruitStage.ENROLLED,
    "accepted": RecruitStage.ENROLLED,
    "commissioned": RecruitStage.COMMISSIONED,
    "declined": RecruitStage.DECLINED,
    "not_interested": RecruitStage.DECLINED,
    "rejected": RecruitStage.DECLINED,
    "withdrawn": RecruitStage.DECLINED,
}


def _stage_for(old_status: str | None) -> str:
    if not old_status:
        return RecruitStage.LEAD.value
    return _STATUS_TO_STAGE.get(old_status.strip().lower(), RecruitStage.LEAD).value


def _utc(dt: Any) -> datetime | None:
    """Coerce a source value to a tz-aware UTC datetime.

    A real Postgres source yields ``datetime`` objects; a SQLite source (or a
    rehearsal dump) yields ISO strings. Both are handled; naive values are
    assumed to be UTC (matching the old app's ``datetime.utcnow`` convention).
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _date(d: Any) -> date | None:
    if d is None:
        return None
    if isinstance(d, str):
        return date.fromisoformat(d[:10])
    if isinstance(d, datetime):
        return d.date()
    return d


def _time(t: Any) -> time | None:
    if t is None:
        return None
    if isinstance(t, str):
        return time.fromisoformat(t)
    return t


def _rows(src: Session, table: str) -> list[dict[str, Any]]:
    """Return all rows of a source table as dicts, or [] if it doesn't exist."""
    if not inspect(src.bind).has_table(table):
        print(f"  ! source table '{table}' not found — skipping")
        return []
    result = src.execute(text(f'SELECT * FROM "{table}"'))  # noqa: S608 (fixed table names)
    return [dict(m) for m in result.mappings().all()]


# (source_table, target_model, field-copy list). Order respects FK dependencies.
def _copy(row: dict, fields: list[str]) -> dict:
    return {f: row.get(f) for f in fields}


def migrate(src: Session, dst: Session, *, dry_run: bool) -> dict[str, int]:
    counts: dict[str, int] = {}

    # 1) Users (old table 'user' -> new 'users'). 2FA reset on purpose.
    users = _rows(src, "user")
    counts["users"] = len(users)
    if not dry_run:
        for r in users:
            dst.add(User(
                id=r["id"],
                username=r["username"],
                email=r["email"],
                password_hash=r["password_hash"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                phone=r.get("phone"),
                role=r.get("role") or "recruiter",
                is_active=bool(r.get("is_active", True)),
                is_locked=bool(r.get("is_locked", False)),
                failed_login_attempts=r.get("failed_login_attempts") or 0,
                password_changed_at=_utc(r.get("password_changed_at")),
                password_expires_at=_utc(r.get("password_expires_at")),
                force_password_change=bool(r.get("force_password_change", False)),
                secret_question=r.get("secret_question") or "Set after login",
                secret_answer_hash=r.get("secret_answer_hash") or "",
                # 2FA reset (see module docstring).
                totp_secret=None,
                totp_enabled=False,
                backup_codes_hash=None,
                totp_setup_completed=False,
                can_enable_2fa=bool(r.get("can_enable_2fa", True)),
                created_at=_utc(r.get("created_at")),
                last_modified=_utc(r.get("last_modified")),
            ))
        dst.flush()

    # 2) Potential recruits (+ baseline stage event).
    recruits = _rows(src, "potential_recruit")
    counts["potential_recruit"] = len(recruits)
    counts["recruit_stage_event"] = 0
    if not dry_run:
        for r in recruits:
            stage = _stage_for(r.get("status"))
            dst.add(PotentialRecruit(
                id=r["id"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                email=r.get("email"),
                phone=r.get("phone"),
                major=r.get("major"),
                current_school=r.get("current_school") or "Unknown",
                school_type=r.get("school_type") or "high_school",
                high_school_graduation_year=r.get("high_school_graduation_year"),
                expected_college_graduation_year=r.get("expected_college_graduation_year"),
                gpa=r.get("gpa"),
                sat_score=r.get("sat_score"),
                act_score=r.get("act_score"),
                interests=r.get("interests"),
                notes=r.get("notes"),
                stage=stage,
                created_at=_utc(r.get("created_at")),
                last_modified=_utc(r.get("last_modified")),
            ))
            # Seed one immutable baseline transition so analytics have history.
            dst.add(RecruitStageEvent(
                recruit_id=r["id"],
                from_stage=None,
                to_stage=stage,
                changed_at=_utc(r.get("created_at")) or datetime.now(UTC),
                changed_by_id=None,
                note="Imported from legacy system",
            ))
            counts["recruit_stage_event"] += 1
        dst.flush()

    # 3) Cadets.
    cadets = _rows(src, "cadet")
    counts["cadet"] = len(cadets)
    if not dry_run:
        cadet_fields = [
            "id", "first_name", "last_name", "email", "phone", "major",
            "graduation_year", "cadet_rank", "hometown", "officer_interest",
            "status", "unenrollment_reason", "gpa",
        ]
        for r in cadets:
            data = _copy(r, cadet_fields)
            data["status"] = data.get("status") or "active"
            data["unenrollment_date"] = _date(r.get("unenrollment_date"))
            data["created_at"] = _utc(r.get("created_at"))
            data["last_modified"] = _utc(r.get("last_modified"))
            dst.add(Cadet(**data))
        dst.flush()

    # 4) University/HS contacts.
    contacts = _rows(src, "university_contact")
    counts["university_contact"] = len(contacts)
    if not dry_run:
        for r in contacts:
            dst.add(UniversityContact(
                id=r["id"],
                university_name=r["university_name"],
                contact_name=r["contact_name"],
                contact_title=r.get("contact_title"),
                email=r.get("email") or "",
                phone=r.get("phone"),
                address=r.get("address"),
                notes=r.get("notes"),
                is_active=bool(r.get("is_active", True)),
                created_at=_utc(r.get("created_at")),
                last_modified=_utc(r.get("last_modified")),
            ))
        dst.flush()

    # 5) Recruitment events (FK -> university_contact).
    events = _rows(src, "recruitment_event")
    counts["recruitment_event"] = len(events)
    if not dry_run:
        for r in events:
            dst.add(RecruitmentEvent(
                id=r["id"],
                title=r["title"],
                description=r.get("description"),
                event_date=_date(r["event_date"]),
                start_time=_time(r.get("start_time")),
                end_time=_time(r.get("end_time")),
                location=r.get("location"),
                university_id=r.get("university_id"),
                event_type=r.get("event_type") or "other",
                status=r.get("status") or "scheduled",
                attendees_count=r.get("attendees_count") or 0,
                notes=r.get("notes"),
                created_at=_utc(r.get("created_at")),
                last_modified=_utc(r.get("last_modified")),
            ))
        dst.flush()

    # 6) External links.
    links = _rows(src, "external_link")
    counts["external_link"] = len(links)
    if not dry_run:
        link_fields = [
            "id", "title", "url", "description", "category", "is_active", "sort_order",
        ]
        for r in links:
            data = _copy(r, link_fields)
            data["created_at"] = _utc(r.get("created_at"))
            data["last_modified"] = _utc(r.get("last_modified"))
            dst.add(ExternalLink(**data))
        dst.flush()

    # 7) Recruitment documents (metadata only; file bytes/blob_url stay empty).
    docs = _rows(src, "recruitment_document")
    counts["recruitment_document"] = len(docs)
    if not dry_run:
        doc_fields = [
            "id", "title", "description", "filename", "original_filename",
            "file_size", "file_type", "category", "is_active", "sort_order",
        ]
        for r in docs:
            data = _copy(r, doc_fields)
            data["created_at"] = _utc(r.get("created_at"))
            data["last_modified"] = _utc(r.get("last_modified"))
            dst.add(RecruitmentDocument(**data))
        dst.flush()

    # 8) Activity log (FK -> users).
    logs = _rows(src, "activity_log")
    counts["activity_log"] = len(logs)
    if not dry_run:
        for r in logs:
            dst.add(ActivityLog(
                id=r["id"],
                user_id=r["user_id"],
                username=r.get("username") or "",
                action=r.get("action") or "UNKNOWN",
                table_name=r.get("table_name"),
                record_id=r.get("record_id"),
                record_description=r.get("record_description"),
                details=r.get("details"),
                ip_address=r.get("ip_address"),
                user_agent=r.get("user_agent"),
                created_at=_utc(r.get("created_at")),
            ))
        dst.flush()

    # 9) Password history (FK -> users).
    pw = _rows(src, "password_history")
    counts["password_history"] = len(pw)
    if not dry_run:
        for r in pw:
            dst.add(PasswordHistory(
                id=r["id"],
                user_id=r["user_id"],
                password_hash=r["password_hash"],
                created_at=_utc(r.get("created_at")),
            ))
        dst.flush()

    return counts


def _resync_sequences(dst: Session) -> None:
    """Postgres only: bump each identity sequence past the max imported id."""
    if dst.bind.dialect.name != "postgresql":
        return
    tables = [
        "users", "potential_recruit", "recruit_stage_event", "cadet",
        "university_contact", "recruitment_event", "external_link",
        "recruitment_document", "activity_log", "password_history",
    ]
    for t in tables:
        dst.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {t}), 1))"
        ))
    dst.commit()


def _wipe(dst: Session) -> None:
    """Delete target rows in reverse-FK order (for reruns/rehearsals)."""
    for model in [
        PasswordHistory, ActivityLog, RecruitmentDocument, ExternalLink,
        RecruitmentEvent, UniversityContact, Cadet, RecruitStageEvent,
        PotentialRecruit, User,
    ]:
        dst.query(model).delete()
    dst.commit()


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate legacy Neon data into the new schema.")
    ap.add_argument("--wipe", action="store_true", help="clear target tables first")
    ap.add_argument("--dry-run", action="store_true", help="read + count only, write nothing")
    args = ap.parse_args()

    source_url = os.environ.get("SOURCE_DATABASE_URL")
    if not source_url:
        print("ERROR: set SOURCE_DATABASE_URL to the legacy Neon database.", file=sys.stderr)
        return 2
    target_url = settings.database_url

    print(f"Source: {source_url.split('@')[-1]}")
    print(f"Target: {target_url.split('@')[-1]}")
    if args.dry_run:
        print("(dry run — no writes)")

    src_engine = create_engine(source_url)
    dst_engine = create_engine(target_url)

    # Guardrail: the target must already be migrated (alembic upgrade head).
    if not inspect(dst_engine).has_table("users") and not args.dry_run:
        print("ERROR: target has no 'users' table. Run `alembic upgrade head` first.",
              file=sys.stderr)
        return 2

    with Session(src_engine) as src, Session(dst_engine) as dst:
        if args.wipe and not args.dry_run:
            print("Wiping target tables...")
            _wipe(dst)

        counts = migrate(src, dst, dry_run=args.dry_run)

        if not args.dry_run:
            dst.commit()
            _resync_sequences(dst)

        # Verify: compare target row counts against what we read.
        print("\nRow counts (source_read -> target):")
        model_by_name = {
            "users": User, "potential_recruit": PotentialRecruit,
            "recruit_stage_event": RecruitStageEvent, "cadet": Cadet,
            "university_contact": UniversityContact, "recruitment_event": RecruitmentEvent,
            "external_link": ExternalLink, "recruitment_document": RecruitmentDocument,
            "activity_log": ActivityLog, "password_history": PasswordHistory,
        }
        ok = True
        for name, read in counts.items():
            model = model_by_name[name]
            actual = (
                dst.scalar(select(func.count()).select_from(model))
                if not args.dry_run else "-"
            )
            flag = ""
            if not args.dry_run and name != "recruit_stage_event" and actual != read:
                flag, ok = "  <-- MISMATCH", False
            print(f"  {name:22} {read:>6} -> {actual}{flag}")

    print("\nDone." if ok else "\nDone WITH MISMATCHES — review above.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
