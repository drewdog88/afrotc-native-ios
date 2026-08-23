# Public "Request Information" Intake Form — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public, unauthenticated "Request Information" form (web only) that creates a `PotentialRecruit` lead, notifies a recruiter and acknowledges the applicant by email, and is protected by Cloudflare Turnstile — plus admin-configurable notification email and acknowledgment template with web + iOS parity.

**Architecture:** A new unauthenticated FastAPI router (`intake`) creates `PotentialRecruit` rows (`stage=LEAD`, `source="public_intake_form"`) exactly as the authenticated flow does, then best-effort sends two plain-text emails via Resend. The DB write is committed *before* any email attempt, so email/provider failures never fail the applicant's submission. Admin-editable settings live in a purpose-built single-row `intake_settings` table exposed through the existing admin router.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · Neon Postgres · Pydantic v2 · React 19 + TypeScript + Vite · SwiftUI · Resend (email, via `httpx`) · Cloudflare Turnstile · pytest.

**Spec:** `docs/superpowers/specs/2026-08-23-request-info-intake-form-design.md`

## Global Constraints

- Python must run under `uv run` (per repo `CLAUDE.md`); Python ≥ 3.11.
- Backend endpoints are **synchronous** `def` handlers taking a `Session` via `Depends(get_db)` — match the existing style; do not introduce `async def` DB handlers.
- Schema (DDL) is owned exclusively by **Alembic**; the app never calls `create_all` in production. Tests use in-memory SQLite via `conftest.py` and call `Base.metadata.create_all` themselves.
- The database is **Postgres-only** at runtime; there is no local/SQLite fallback (config rejects any non-`postgresql` URL).
- The repo is **PUBLIC**. Never commit secrets. `resend_api_key`, `turnstile_secret_key`, `resend_from_email`, and the Turnstile **site** key are supplied via environment only.
- The acknowledgment email is **plain text** (never HTML) — this is a security requirement (applicant-controlled `first_name` is substituted in).
- The API contract is `shared/openapi.json`; after any API change, re-export it and regenerate `web/src/api/schema.d.ts`. Web/iOS build against that contract.
- New enum string values must be lowercase snake (matches `enums.py` convention).
- The intake form is **web-only**. iOS gets the **admin settings** screens only, never the public form.

---

## File Structure

**Backend (new):**
- `backend/app/models/settings.py` — `IntakeSettings` model (single-row config table).
- `backend/app/schemas/intake.py` — `IntakeCreate`, `IntakeSubmitResult`, `IntakeOptions`, `IntakeSettingsOut`, `IntakeSettingsUpdate`.
- `backend/app/services/email.py` — Resend wrapper + the two message builders.
- `backend/app/services/spam.py` — Turnstile verification + IP rate-limit helpers.
- `backend/app/api/v1/intake.py` — public `POST /intake`, `GET /intake/options`.
- `backend/alembic/versions/<hash>_intake_form.py` — migration.
- `backend/tests/test_intake.py`, `backend/tests/test_intake_settings.py`.

**Backend (modify):**
- `backend/app/models/enums.py` — `GradeLevel`, `IntendedTerm`, extend `SchoolType`.
- `backend/app/models/recruit.py` — new columns on `PotentialRecruit`.
- `backend/app/models/__init__.py` — register `IntakeSettings`.
- `backend/app/core/config.py` — `resend_api_key`, `resend_from_email`, `turnstile_secret_key`.
- `backend/app/bootstrap.py` — seed the default `IntakeSettings` row.
- `backend/app/main.py` — call the settings seed in lifespan.
- `backend/app/api/v1/admin.py` — `GET/PUT /admin/intake-settings`.
- `backend/app/api/v1/router.py` — mount `intake.router`.
- `backend/pyproject.toml` — add `httpx` to runtime deps.

**Web (new):** `web/src/pages/RequestInfo.tsx`, `web/src/pages/RequestInfo.module.css`.
**Web (modify):** `web/src/api/schema.d.ts` (regenerated), `web/src/lib/api.ts`, `web/src/main.tsx`, `web/src/pages/Admin.tsx`, `web/src/pages/Admin.module.css`, `web/src/pages/Recruits.tsx`, `vercel.json`.

**iOS (modify):** `ios/Det695/Models/Admin.swift`, `ios/Det695/Networking/APIClient.swift`, `ios/Det695/Views/AdminView.swift`.

---

## Task 1: Enums + model columns + `IntakeSettings` + migration

**Files:**
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/models/recruit.py`
- Create: `backend/app/models/settings.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/<hash>_intake_form.py`
- Test: `backend/tests/test_intake.py` (schema-shape test only in this task)

**Interfaces:**
- Produces: `GradeLevel`, `IntendedTerm`, `SchoolType.OTHER` in `app.models.enums`; new columns `grade_level`, `intended_entry_term`, `intended_entry_year`, `consent_given_at`, `acknowledgment_email_sent_at`, `source` (default `"manual"`), `source_ip` on `PotentialRecruit`; `IntakeSettings` model (`id`, `recruiter_notification_email`, `ack_email_subject`, `ack_email_body`, timestamps) exported from `app.models`.

- [ ] **Step 1: Add the enums**

In `backend/app/models/enums.py`, extend `SchoolType` and add two new enums:

```python
class SchoolType(StrEnum):
    HIGH_SCHOOL = "high_school"
    COLLEGE = "college"
    OTHER = "other"  # GED / community college / non-standard path


class GradeLevel(StrEnum):
    HS_9 = "hs_9"
    HS_10 = "hs_10"
    HS_11 = "hs_11"
    HS_12 = "hs_12"
    COLLEGE_FRESHMAN = "college_freshman"
    COLLEGE_SOPHOMORE = "college_sophomore"
    COLLEGE_JUNIOR = "college_junior"
    COLLEGE_SENIOR = "college_senior"
    OTHER = "other"


class IntendedTerm(StrEnum):
    FALL = "fall"
    SPRING = "spring"


# Maps a submitted grade level to the school_type stored on the recruit.
# OTHER stays OTHER (never silently labeled college).
def school_type_for_grade(grade: GradeLevel) -> SchoolType:
    if grade in (GradeLevel.HS_9, GradeLevel.HS_10, GradeLevel.HS_11, GradeLevel.HS_12):
        return SchoolType.HIGH_SCHOOL
    if grade == GradeLevel.OTHER:
        return SchoolType.OTHER
    return SchoolType.COLLEGE
```

- [ ] **Step 2: Add the columns on `PotentialRecruit`**

In `backend/app/models/recruit.py`, add these columns to the `PotentialRecruit` class (after `notes`, before the `stage` column). Note `source` has a server-side default so existing rows/inserts are unaffected:

```python
    # Public-intake fields (nullable — the authenticated create flow leaves them unset).
    grade_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    intended_entry_term: Mapped[str | None] = mapped_column(String(10), nullable=True)
    intended_entry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledgment_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
```

`String` and `Integer` and `DateTime` are already imported in this file; confirm and add any missing import.

- [ ] **Step 3: Create the `IntakeSettings` model**

Create `backend/app/models/settings.py`:

```python
"""Singleton configuration for the public request-info intake form."""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin

DEFAULT_ACK_SUBJECT = "Thanks for your interest in AFROTC Detachment 695"
DEFAULT_ACK_BODY = (
    "Hi {{first_name}},\n\n"
    "Thank you for your interest in Air Force ROTC Detachment 695. "
    "We received your information and a recruiter will reach out to you soon.\n\n"
    "In the meantime, you can learn more about the program here:\n"
    "https://www.afrotc.com\n\n"
    "Go forth and conquer,\n"
    "AFROTC Detachment 695"
)


class IntakeSettings(Base, TimestampMixin):
    """One row (id=1) holding admin-editable intake configuration."""

    __tablename__ = "intake_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    recruiter_notification_email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ack_email_subject: Mapped[str] = mapped_column(String(200), default=DEFAULT_ACK_SUBJECT)
    ack_email_body: Mapped[str] = mapped_column(Text, default=DEFAULT_ACK_BODY)
```

- [ ] **Step 4: Register the model**

In `backend/app/models/__init__.py`, import and add to `__all__`:

```python
from app.models.settings import IntakeSettings
```
Add `"IntakeSettings"` (and the new enums `"GradeLevel"`, `"IntendedTerm"` if you choose to re-export enums here — match existing style; enums are currently re-exported, so add `GradeLevel` and `IntendedTerm` to both the `from app.models.enums import (...)` block and `__all__`).

- [ ] **Step 5: Write a failing test that the new model + columns import and instantiate**

Create `backend/tests/test_intake.py`:

```python
"""Public intake form: model shape, submission, spam gate, email best-effort."""
from __future__ import annotations

from app.models import IntakeSettings, PotentialRecruit
from app.models.enums import GradeLevel, IntendedTerm, SchoolType, school_type_for_grade


def test_new_recruit_columns_exist() -> None:
    r = PotentialRecruit(
        first_name="Pat", last_name="Cadet", current_school="Lincoln HS",
        grade_level=GradeLevel.HS_11.value, intended_entry_term=IntendedTerm.FALL.value,
        intended_entry_year=2027, source="public_intake_form", source_ip="203.0.113.7",
    )
    assert r.source == "public_intake_form"
    assert r.acknowledgment_email_sent_at is None


def test_intake_settings_defaults() -> None:
    s = IntakeSettings()
    assert s.recruiter_notification_email is None


def test_school_type_derivation() -> None:
    assert school_type_for_grade(GradeLevel.HS_11) == SchoolType.HIGH_SCHOOL
    assert school_type_for_grade(GradeLevel.COLLEGE_JUNIOR) == SchoolType.COLLEGE
    assert school_type_for_grade(GradeLevel.OTHER) == SchoolType.OTHER
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_intake.py -v`
Expected: PASS (the `_fresh_schema` fixture builds the SQLite tables from the models, so the new table/columns exist in-memory). If import errors appear, fix the model wiring before proceeding.

- [ ] **Step 7: Create the Alembic migration**

Generate an empty revision (this does NOT need a DB connection):
```bash
cd backend && uv run alembic revision -m "intake form: recruit columns + intake_settings"
```
Confirm the current head first with `uv run alembic heads`; the generated file's `down_revision` should already point at it (the initial schema `2082358eabfe` unless newer migrations exist). Fill in the body:

```python
def upgrade() -> None:
    op.create_table(
        "intake_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recruiter_notification_email", sa.String(length=120), nullable=True),
        sa.Column("ack_email_subject", sa.String(length=200), nullable=False),
        sa.Column("ack_email_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("potential_recruit", schema=None) as batch_op:
        batch_op.add_column(sa.Column("grade_level", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("intended_entry_term", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("intended_entry_year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("acknowledgment_email_sent_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("source", sa.String(length=20), server_default="manual", nullable=False))
        batch_op.add_column(sa.Column("source_ip", sa.String(length=45), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("potential_recruit", schema=None) as batch_op:
        batch_op.drop_column("source_ip")
        batch_op.drop_column("source")
        batch_op.drop_column("acknowledgment_email_sent_at")
        batch_op.drop_column("consent_given_at")
        batch_op.drop_column("intended_entry_year")
        batch_op.drop_column("intended_entry_term")
        batch_op.drop_column("grade_level")
    op.drop_table("intake_settings")
```
Ensure `import sqlalchemy as sa` and `from alembic import op` are present (the revision template includes them). Do NOT run `alembic upgrade` here — that happens against Neon in Task 12 (rollout).

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/enums.py backend/app/models/recruit.py backend/app/models/settings.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_intake.py
git commit -m "feat(intake): add grade/term/consent/source columns + intake_settings model + migration"
```

---

## Task 2: Config fields + bootstrap seed for `IntakeSettings`

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/bootstrap.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_intake_settings.py`

**Interfaces:**
- Consumes: `IntakeSettings` from Task 1.
- Produces: `settings.resend_api_key`, `settings.resend_from_email`, `settings.turnstile_secret_key`; `bootstrap_intake_settings(db)` in `app.bootstrap`; a guaranteed `intake_settings` row with `id=1` after lifespan runs.

- [ ] **Step 1: Add config fields**

In `backend/app/core/config.py`, inside `Settings`, after the CORS block:

```python
    # Email (Resend) — REQUIRED in production for intake acknowledgments.
    # Empty disables sending (local/dev): submissions still succeed, emails are skipped.
    resend_api_key: str = ""
    resend_from_email: str = ""  # must be on a domain verified in Resend

    # Cloudflare Turnstile secret (server-side verify). Empty disables verification
    # (local/dev) — set in production so the public form is bot-protected.
    turnstile_secret_key: str = ""
```

- [ ] **Step 2: Write a failing test for the seed**

Create `backend/tests/test_intake_settings.py`:

```python
"""Admin intake-settings endpoints + bootstrap seed."""
from __future__ import annotations

from app.bootstrap import bootstrap_intake_settings
from app.models import IntakeSettings
from tests.conftest import TestingSessionLocal


def test_bootstrap_seeds_single_settings_row() -> None:
    with TestingSessionLocal() as db:
        bootstrap_intake_settings(db)
        bootstrap_intake_settings(db)  # idempotent — second call is a no-op
        rows = db.query(IntakeSettings).all()
        assert len(rows) == 1
        assert rows[0].id == 1
        assert rows[0].ack_email_subject  # default is non-empty
```

- [ ] **Step 3: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/test_intake_settings.py::test_bootstrap_seeds_single_settings_row -v`
Expected: FAIL with `ImportError` (no `bootstrap_intake_settings`).

- [ ] **Step 4: Implement the seed**

In `backend/app/bootstrap.py`, add:

```python
from app.models import IntakeSettings  # add to existing imports


def bootstrap_intake_settings(db: Session) -> None:
    """Ensure the single intake_settings row (id=1) exists, with defaults."""
    existing = db.get(IntakeSettings, 1)
    if existing is not None:
        return
    db.add(IntakeSettings(id=1))
    db.commit()
    logger.info("Seeded default intake_settings row.")
```

- [ ] **Step 5: Call the seed from lifespan**

In `backend/app/main.py`, update the lifespan body:

```python
    from app.bootstrap import bootstrap_admin, bootstrap_intake_settings

    with SessionLocal() as db:
        bootstrap_admin(db)
        bootstrap_intake_settings(db)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/test_intake_settings.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/config.py backend/app/bootstrap.py backend/app/main.py backend/tests/test_intake_settings.py
git commit -m "feat(intake): config for Resend/Turnstile + seed default intake_settings row"
```

---

## Task 3: Email service (Resend, plain text)

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/services/email.py`
- Test: `backend/tests/test_intake.py` (append)

**Interfaces:**
- Produces:
  - `send_email(to: str, subject: str, body: str) -> bool` — low-level plain-text send via Resend; returns `True` on success, `False` (logged) on any failure or when `resend_api_key`/`resend_from_email` is unset. Never raises.
  - `render_ack(subject_template: str, body_template: str, first_name: str) -> tuple[str, str]` — substitutes `{{first_name}}` into subject and body (plain text; no escaping needed).
  - `build_recruiter_notification(recruit) -> tuple[str, str]` — returns `(subject, body)` summarizing a new lead.

- [ ] **Step 1: Add `httpx` runtime dependency**

In `backend/pyproject.toml`, add to `[project].dependencies`:
```toml
    "httpx>=0.28",
```
(It is already a dev dep; promoting it to runtime is intentional — the serverless function calls Resend and Turnstile over HTTPS.) Then run `cd backend && uv sync`.

- [ ] **Step 2: Write failing tests for rendering**

Append to `backend/tests/test_intake.py`:

```python
from app.services.email import build_recruiter_notification, render_ack


def test_render_ack_substitutes_first_name() -> None:
    subject, body = render_ack("Hi {{first_name}}", "Hello {{first_name}}!", "Dana")
    assert subject == "Hi Dana"
    assert body == "Hello Dana!"


def test_render_ack_plain_text_is_not_html_escaped() -> None:
    # Plain text: whatever the applicant typed is inserted verbatim (no markup context).
    _, body = render_ack("s", "Hi {{first_name}}", "<b>x</b>")
    assert body == "Hi <b>x</b>"


def test_build_recruiter_notification_includes_key_fields() -> None:
    from app.models import PotentialRecruit
    r = PotentialRecruit(
        first_name="Sam", last_name="Lee", email="sam@example.com", phone="503-555-0100",
        current_school="Grant HS", grade_level="hs_12", intended_entry_term="fall",
        intended_entry_year=2027,
    )
    subject, body = build_recruiter_notification(r)
    assert "Sam Lee" in body
    assert "sam@example.com" in body
    assert "Grant HS" in body
```

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_intake.py -k "render_ack or recruiter_notification" -v`
Expected: FAIL (`ModuleNotFoundError: app.services.email`).

- [ ] **Step 4: Implement the email service**

Create `backend/app/services/email.py`:

```python
"""Transactional email via Resend. Plain-text only.

All sends are best-effort: failures are logged and swallowed so a public
submission is never turned into an error by a downstream email problem.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("afrotc695.email")

_RESEND_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False otherwise."""
    if not settings.resend_api_key or not settings.resend_from_email:
        logger.warning("Email not configured (resend_api_key/from unset); skipping send to %s.", to)
        return False
    if not to:
        return False
    try:
        resp = httpx.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.resend_from_email,
                "to": [to],
                "subject": subject,
                "text": body,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort; never propagate
        logger.error("Resend send to %s failed: %s", to, exc)
        return False


def render_ack(subject_template: str, body_template: str, first_name: str) -> tuple[str, str]:
    return (
        subject_template.replace("{{first_name}}", first_name),
        body_template.replace("{{first_name}}", first_name),
    )


def build_recruiter_notification(recruit) -> tuple[str, str]:
    """Subject/body for the internal 'new lead' notification."""
    subject = f"New AFROTC interest: {recruit.first_name} {recruit.last_name}"
    lines = [
        "A new request-information form was submitted:",
        "",
        f"Name:    {recruit.first_name} {recruit.last_name}",
        f"Email:   {recruit.email or '-'}",
        f"Phone:   {recruit.phone or '-'}",
        f"School:  {recruit.current_school}",
        f"Grade:   {recruit.grade_level or '-'}",
        f"Term:    {recruit.intended_entry_term or '-'} {recruit.intended_entry_year or ''}".rstrip(),
        "",
        "Open the recruiting dashboard to view this lead.",
    ]
    return subject, "\n".join(lines)
```

- [ ] **Step 5: Run to verify passes**

Run: `cd backend && uv run pytest tests/test_intake.py -k "render_ack or recruiter_notification" -v`
Expected: PASS. (No network: `send_email` is not called here.)

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/app/services/email.py backend/tests/test_intake.py
git commit -m "feat(intake): Resend plain-text email service + message builders"
```

---

## Task 4: Spam protection (Turnstile verify + IP rate limit)

**Files:**
- Create: `backend/app/services/spam.py`
- Test: `backend/tests/test_intake.py` (append)

**Interfaces:**
- Produces:
  - `verify_turnstile(token: str, remote_ip: str | None) -> bool` — validates against Cloudflare siteverify. Returns `True` when `turnstile_secret_key` is unset (dev/test mode, logs a warning). Returns `False` on failure. Never raises.
  - `client_ip(request) -> str | None` — first hop of `X-Forwarded-For`, else `request.client.host`.
  - `RATE_LIMIT_PER_HOUR = 30` and `too_many_from_ip(db, ip) -> bool` — counts `PotentialRecruit` rows with matching `source_ip` created in the last hour.

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_intake.py`:

```python
def test_verify_turnstile_dev_mode_passes(monkeypatch) -> None:
    from app.core.config import settings
    from app.services import spam
    monkeypatch.setattr(settings, "turnstile_secret_key", "", raising=False)
    assert spam.verify_turnstile("anything", "203.0.113.1") is True


def test_client_ip_prefers_forwarded_for() -> None:
    from app.services.spam import client_ip

    class _Req:
        headers = {"x-forwarded-for": "198.51.100.9, 10.0.0.1"}
        class client:  # noqa: N801
            host = "10.0.0.1"

    assert client_ip(_Req()) == "198.51.100.9"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_intake.py -k "turnstile or client_ip" -v`
Expected: FAIL (`ModuleNotFoundError: app.services.spam`).

- [ ] **Step 3: Implement**

Create `backend/app/services/spam.py`:

```python
"""Public-form abuse defenses: Cloudflare Turnstile + a loose IP rate-limit.

Turnstile is the PRIMARY bot defense. The IP rate-limit is only a high
threshold backstop — a recruiting table or classroom on shared WiFi shares one
NAT'd IP, so a low cap would reject legitimate recruits.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import now_utc
from app.models import PotentialRecruit

logger = logging.getLogger("afrotc695.spam")

_SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
RATE_LIMIT_PER_HOUR = 30


def client_ip(request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", None)


def verify_turnstile(token: str, remote_ip: str | None) -> bool:
    if not settings.turnstile_secret_key:
        logger.warning("TURNSTILE_SECRET_KEY unset; skipping verification (dev mode).")
        return True
    if not token:
        return False
    try:
        resp = httpx.post(
            _SITEVERIFY_URL,
            data={"secret": settings.turnstile_secret_key, "response": token, "remoteip": remote_ip or ""},
            timeout=10.0,
        )
        resp.raise_for_status()
        return bool(resp.json().get("success"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Turnstile verify failed: %s", exc)
        return False


def too_many_from_ip(db: Session, ip: str | None) -> bool:
    if not ip:
        return False
    since = now_utc() - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(PotentialRecruit)
        .where(PotentialRecruit.source_ip == ip, PotentialRecruit.created_at >= since)
    ) or 0
    return count >= RATE_LIMIT_PER_HOUR
```

- [ ] **Step 4: Run to verify passes**

Run: `cd backend && uv run pytest tests/test_intake.py -k "turnstile or client_ip" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/spam.py backend/tests/test_intake.py
git commit -m "feat(intake): Turnstile verification + loose IP rate-limit backstop"
```

---

## Task 5: Intake schemas + public router

**Files:**
- Create: `backend/app/schemas/intake.py`
- Create: `backend/app/api/v1/intake.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_intake.py` (append)

**Interfaces:**
- Consumes: `send_email`, `render_ack`, `build_recruiter_notification` (Task 3); `verify_turnstile`, `too_many_from_ip`, `client_ip` (Task 4); `school_type_for_grade`, enums (Task 1); `IntakeSettings` seed (Task 2).
- Produces: `POST /api/v1/intake` (public), `GET /api/v1/intake/options` (public). `IntakeCreate`, `IntakeSubmitResult`, `IntakeOptions` schemas.

- [ ] **Step 1: Create the schemas**

Create `backend/app/schemas/intake.py`:

```python
"""Public request-info intake schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import GradeLevel, IntendedTerm


class IntakeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    current_school: str
    grade_level: GradeLevel
    intended_entry_term: IntendedTerm
    intended_entry_year: int
    consent: bool
    turnstile_token: str = ""

    @field_validator("consent")
    @classmethod
    def _must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Consent to be contacted is required.")
        return v

    @field_validator("intended_entry_year")
    @classmethod
    def _reasonable_year(cls, v: int) -> int:
        if v < 2000 or v > 2100:
            raise ValueError("Enter a valid year.")
        return v


class IntakeSubmitResult(BaseModel):
    ok: bool = True
    message: str = "Thanks! A recruiter will be in touch soon."


class _Option(BaseModel):
    value: str
    label: str


class IntakeOptions(BaseModel):
    grade_levels: list[_Option]
    terms: list[_Option]
```

- [ ] **Step 2: Write failing endpoint tests**

Append to `backend/tests/test_intake.py`:

```python
from fastapi.testclient import TestClient

from app.models import PotentialRecruit
from tests.conftest import TestingSessionLocal

_VALID = {
    "first_name": "Jamie", "last_name": "Rivera", "email": "jamie@example.com",
    "phone": "503-555-0142", "current_school": "Cleveland HS", "grade_level": "hs_11",
    "intended_entry_term": "fall", "intended_entry_year": 2027, "consent": True,
    "turnstile_token": "test",
}


def _emails(monkeypatch):
    """Capture email sends without hitting the network."""
    sent = []
    import app.api.v1.intake as intake_mod
    monkeypatch.setattr(intake_mod, "send_email", lambda to, subject, body: (sent.append(to) or True))
    return sent


def test_options_are_public(client: TestClient) -> None:
    resp = client.get("/api/v1/intake/options")
    assert resp.status_code == 200
    body = resp.json()
    assert any(o["value"] == "hs_11" for o in body["grade_levels"])
    assert {o["value"] for o in body["terms"]} == {"fall", "spring"}


def test_valid_submission_creates_lead_and_sends_both_emails(client, monkeypatch) -> None:
    # Configure a recruiter address so the notification email is attempted.
    with TestingSessionLocal() as db:
        from app.bootstrap import bootstrap_intake_settings
        from app.models import IntakeSettings
        bootstrap_intake_settings(db)
        db.get(IntakeSettings, 1).recruiter_notification_email = "recruiter@det695.local"
        db.commit()
    sent = _emails(monkeypatch)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 201, resp.text
    assert resp.json()["ok"] is True
    with TestingSessionLocal() as db:
        rows = db.query(PotentialRecruit).all()
        assert len(rows) == 1
        assert rows[0].stage == "lead"
        assert rows[0].source == "public_intake_form"
        assert rows[0].school_type == "high_school"
        assert rows[0].consent_given_at is not None
        assert rows[0].acknowledgment_email_sent_at is not None
    assert "jamie@example.com" in sent          # applicant ack
    assert "recruiter@det695.local" in sent      # recruiter notification


def test_missing_consent_is_422(client, monkeypatch) -> None:
    _emails(monkeypatch)
    bad = {**_VALID, "consent": False}
    assert client.post("/api/v1/intake", json=bad).status_code == 422


def test_failed_turnstile_is_400_and_no_row(client, monkeypatch) -> None:
    import app.api.v1.intake as intake_mod
    monkeypatch.setattr(intake_mod, "verify_turnstile", lambda token, ip: False)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 400
    with TestingSessionLocal() as db:
        assert db.query(PotentialRecruit).count() == 0


def test_email_failure_still_returns_201(client, monkeypatch) -> None:
    import app.api.v1.intake as intake_mod
    monkeypatch.setattr(intake_mod, "send_email", lambda to, subject, body: False)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 201
    with TestingSessionLocal() as db:
        r = db.query(PotentialRecruit).one()
        assert r.acknowledgment_email_sent_at is None  # ack never confirmed


def test_other_grade_maps_to_other_school_type(client, monkeypatch) -> None:
    _emails(monkeypatch)
    resp = client.post("/api/v1/intake", json={**_VALID, "grade_level": "other"})
    assert resp.status_code == 201
    with TestingSessionLocal() as db:
        assert db.query(PotentialRecruit).one().school_type == "other"
```

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_intake.py -v`
Expected: the new endpoint tests FAIL (404 / import error); the Task 1–4 unit tests still PASS.

- [ ] **Step 4: Implement the router**

Create `backend/app/api/v1/intake.py`:

```python
"""Public, UNAUTHENTICATED request-info intake.

Creates a PotentialRecruit lead (stage=LEAD, source=public_intake_form), then
best-effort emails the recruiter and the applicant. The DB commit is the source
of truth; email/Turnstile-adjacent failures never fail an accepted submission.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import now_utc
from app.models import IntakeSettings, PotentialRecruit, RecruitStageEvent
from app.models.enums import GradeLevel, IntendedTerm, RecruitStage, school_type_for_grade
from app.schemas.intake import IntakeCreate, IntakeOptions, IntakeSubmitResult, _Option
from app.services.email import build_recruiter_notification, render_ack, send_email
from app.services.spam import client_ip, too_many_from_ip, verify_turnstile

router = APIRouter(prefix="/intake", tags=["intake"])

_GRADE_LABELS = {
    GradeLevel.HS_9: "9th grade", GradeLevel.HS_10: "10th grade",
    GradeLevel.HS_11: "11th grade", GradeLevel.HS_12: "12th grade",
    GradeLevel.COLLEGE_FRESHMAN: "College freshman",
    GradeLevel.COLLEGE_SOPHOMORE: "College sophomore",
    GradeLevel.COLLEGE_JUNIOR: "College junior",
    GradeLevel.COLLEGE_SENIOR: "College senior",
    GradeLevel.OTHER: "Other",
}
_TERM_LABELS = {IntendedTerm.FALL: "Fall", IntendedTerm.SPRING: "Spring"}


@router.get("/options", response_model=IntakeOptions)
def intake_options() -> IntakeOptions:
    return IntakeOptions(
        grade_levels=[_Option(value=g.value, label=_GRADE_LABELS[g]) for g in GradeLevel],
        terms=[_Option(value=t.value, label=_TERM_LABELS[t]) for t in IntendedTerm],
    )


@router.post("", response_model=IntakeSubmitResult, status_code=status.HTTP_201_CREATED)
def submit_intake(
    body: IntakeCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> IntakeSubmitResult:
    ip = client_ip(request)

    if not verify_turnstile(body.turnstile_token, ip):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification failed. Please try again.")
    if too_many_from_ip(db, ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many submissions. Please try again later.")

    recruit = PotentialRecruit(
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        email=str(body.email),
        phone=body.phone.strip(),
        current_school=body.current_school.strip(),
        grade_level=body.grade_level.value,
        school_type=school_type_for_grade(body.grade_level).value,
        intended_entry_term=body.intended_entry_term.value,
        intended_entry_year=body.intended_entry_year,
        stage=RecruitStage.LEAD.value,
        source="public_intake_form",
        source_ip=ip,
        consent_given_at=now_utc(),
    )
    db.add(recruit)
    db.flush()  # assign recruit.id
    db.add(RecruitStageEvent(
        recruit_id=recruit.id, from_stage=None, to_stage=recruit.stage,
        changed_by_id=None, note="Submitted public request-info form",
    ))
    db.commit()
    db.refresh(recruit)

    # --- Best-effort notifications (never fail the accepted submission) ---
    settings_row = db.get(IntakeSettings, 1)
    if settings_row and settings_row.recruiter_notification_email:
        subject, notif_body = build_recruiter_notification(recruit)
        send_email(settings_row.recruiter_notification_email, subject, notif_body)

    if settings_row:
        subj, body_text = render_ack(
            settings_row.ack_email_subject, settings_row.ack_email_body, recruit.first_name
        )
        if send_email(recruit.email, subj, body_text):
            recruit.acknowledgment_email_sent_at = now_utc()
            db.commit()

    return IntakeSubmitResult()
```

Note: `send_email`, `verify_turnstile` are imported at module scope so tests can `monkeypatch.setattr(intake_mod, "send_email", ...)`.

- [ ] **Step 5: Mount the router**

In `backend/app/api/v1/router.py`, add `intake` to the imports and include it near the other core entities:
```python
from app.api.v1 import (..., intake, ...)
api_router.include_router(intake.router)
```

- [ ] **Step 6: Run the full intake test file**

Run: `cd backend && uv run pytest tests/test_intake.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/intake.py backend/app/api/v1/intake.py backend/app/api/v1/router.py backend/tests/test_intake.py
git commit -m "feat(intake): public POST /intake + GET /intake/options with spam gate + best-effort email"
```

---

## Task 6: Admin intake-settings endpoints

**Files:**
- Modify: `backend/app/schemas/intake.py`
- Modify: `backend/app/api/v1/admin.py`
- Test: `backend/tests/test_intake_settings.py` (append)

**Interfaces:**
- Consumes: `IntakeSettings`, `require_admin`, `get_db`, `bootstrap_intake_settings`.
- Produces: `GET /api/v1/admin/intake-settings` → `IntakeSettingsOut`; `PUT /api/v1/admin/intake-settings` (body `IntakeSettingsUpdate`) → `IntakeSettingsOut`.

- [ ] **Step 1: Add settings schemas**

Append to `backend/app/schemas/intake.py`:

```python
from app.schemas.common import ORMModel  # add near top imports


class IntakeSettingsOut(ORMModel):
    id: int
    recruiter_notification_email: str | None = None
    ack_email_subject: str
    ack_email_body: str


class IntakeSettingsUpdate(BaseModel):
    recruiter_notification_email: EmailStr | None = None
    ack_email_subject: str | None = None
    ack_email_body: str | None = None
```

- [ ] **Step 2: Write failing tests**

Append to `backend/tests/test_intake_settings.py`:

```python
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_intake_settings_admin_only(client: TestClient, make_user: Callable[..., User], login) -> None:
    make_user("grunt")
    token = login(client, "grunt", "Recruit123!").json()["access_token"]
    assert client.get("/api/v1/admin/intake-settings", headers=_bearer(token)).status_code == 403


def test_admin_gets_and_updates_settings(client: TestClient, auth_headers: dict[str, str]) -> None:
    got = client.get("/api/v1/admin/intake-settings", headers=auth_headers)
    assert got.status_code == 200, got.text
    assert got.json()["ack_email_subject"]  # seeded default

    put = client.put(
        "/api/v1/admin/intake-settings",
        headers=auth_headers,
        json={"recruiter_notification_email": "lead@det695.local", "ack_email_subject": "Welcome!"},
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["recruiter_notification_email"] == "lead@det695.local"
    assert body["ack_email_subject"] == "Welcome!"
```

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_intake_settings.py -v`
Expected: the two new tests FAIL (404).

- [ ] **Step 4: Implement the endpoints**

In `backend/app/api/v1/admin.py`, add imports and two routes:

```python
from app.bootstrap import bootstrap_intake_settings
from app.models import IntakeSettings
from app.schemas.intake import IntakeSettingsOut, IntakeSettingsUpdate


def _settings_row(db: Session) -> IntakeSettings:
    row = db.get(IntakeSettings, 1)
    if row is None:
        bootstrap_intake_settings(db)
        row = db.get(IntakeSettings, 1)
    return row


@router.get("/intake-settings", response_model=IntakeSettingsOut)
def get_intake_settings(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntakeSettings:
    return _settings_row(db)


@router.put("/intake-settings", response_model=IntakeSettingsOut)
def update_intake_settings(
    body: IntakeSettingsUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntakeSettings:
    row = _settings_row(db)
    data = body.model_dump(exclude_unset=True)
    if "recruiter_notification_email" in data and data["recruiter_notification_email"] is not None:
        data["recruiter_notification_email"] = str(data["recruiter_notification_email"])
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
```

- [ ] **Step 5: Run to verify passes**

Run: `cd backend && uv run pytest tests/test_intake_settings.py -v`
Expected: all PASS.

- [ ] **Step 6: Run the whole backend suite**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: all green, no lint errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/intake.py backend/app/api/v1/admin.py backend/tests/test_intake_settings.py
git commit -m "feat(intake): admin GET/PUT /admin/intake-settings"
```

---

## Task 7: Export the OpenAPI contract + regenerate web types

**Files:**
- Modify: `shared/openapi.json` (regenerated)
- Modify: `web/src/api/schema.d.ts` (regenerated)

**Interfaces:**
- Produces: contract entries for `/intake`, `/intake/options`, `/admin/intake-settings`, and the new component schemas (`IntakeCreate`, `IntakeSubmitResult`, `IntakeOptions`, `IntakeSettingsOut`, `IntakeSettingsUpdate`) that Tasks 8–11 consume as generated TS types.

- [ ] **Step 1: Re-export OpenAPI**

Run: `cd backend && uv run python scripts/export_openapi.py`
Expected: prints a path count higher than before; `shared/openapi.json` now contains `/api/v1/intake`.

- [ ] **Step 2: Regenerate the TS types**

Run: `cd web && npx openapi-typescript ../shared/openapi.json -o src/api/schema.d.ts`
Expected: `web/src/api/schema.d.ts` now contains `IntakeCreate`, `IntakeOptions`, `IntakeSettingsOut`, etc.

- [ ] **Step 3: Verify the web build still type-checks**

Run: `cd web && npm install && npm run build`
Expected: build succeeds (no code consumes the new types yet).

- [ ] **Step 4: Commit**

```bash
git add shared/openapi.json web/src/api/schema.d.ts
git commit -m "chore(contract): regenerate openapi.json + web types for intake endpoints"
```

---

## Task 8: Web API client methods + CSP for Turnstile

**Files:**
- Modify: `web/src/lib/api.ts`
- Modify: `vercel.json`

**Interfaces:**
- Consumes: generated types from Task 7.
- Produces: `api.submitIntake(body)`, `api.intakeOptions()`, `api.getIntakeSettings()`, `api.updateIntakeSettings(body)`; exported types `IntakeCreate`, `IntakeOptions`, `IntakeSettingsOut`, `IntakeSettingsUpdate`. CSP that permits `https://challenges.cloudflare.com`.

- [ ] **Step 1: Update the CSP in `vercel.json`**

In the `Content-Security-Policy` value, change `script-src 'self'` to `script-src 'self' https://challenges.cloudflare.com` and add a `frame-src https://challenges.cloudflare.com;` directive. The full value becomes:

```
default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self' https://challenges.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; img-src 'self' data: blob: https://*.basemaps.cartocdn.com; connect-src 'self' https://*.basemaps.cartocdn.com; frame-src https://challenges.cloudflare.com; worker-src blob:; child-src blob:; manifest-src 'self'
```
(Turnstile posts its token to our own `/api/v1/intake`, so `connect-src 'self'` is sufficient; the script + iframe are the parts that need the new allowance.)

- [ ] **Step 2: Add the client methods and types**

In `web/src/lib/api.ts`, add to the exported type aliases block:
```ts
export type IntakeCreate = Schemas["IntakeCreate"];
export type IntakeOptions = Schemas["IntakeOptions"];
export type IntakeSubmitResult = Schemas["IntakeSubmitResult"];
export type IntakeSettingsOut = Schemas["IntakeSettingsOut"];
export type IntakeSettingsUpdate = Schemas["IntakeSettingsUpdate"];
```
Add to the `api` object (submit + options are unauthenticated — use `auth: false`):
```ts
  intakeOptions: () => request<IntakeOptions>("/intake/options", { auth: false }),
  submitIntake: (body: IntakeCreate) =>
    request<IntakeSubmitResult>("/intake", { method: "POST", auth: false, body }),
  getIntakeSettings: () => request<IntakeSettingsOut>("/admin/intake-settings"),
  updateIntakeSettings: (body: IntakeSettingsUpdate) =>
    request<IntakeSettingsOut>("/admin/intake-settings", { method: "PUT", body }),
```

- [ ] **Step 3: Verify type-check**

Run: `cd web && npm run build`
Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/api.ts vercel.json
git commit -m "feat(intake): web API client methods + CSP allowance for Turnstile"
```

---

## Task 9: Public `/request-info` page + route + Turnstile widget

**Files:**
- Create: `web/src/pages/RequestInfo.tsx`
- Create: `web/src/pages/RequestInfo.module.css`
- Modify: `web/src/main.tsx`

**Interfaces:**
- Consumes: `api.intakeOptions()`, `api.submitIntake()` (Task 8); `Insignia` component (already used by `Login.tsx`).
- Produces: a public route at `/request-info` rendered outside `RequireAuth`.

- [ ] **Step 1: Add the route (outside auth)**

In `web/src/main.tsx`, import the page and add a route as a sibling of `/login` (NOT inside the `RequireAuth`/`AppShell` group, and NOT wrapped in `RedirectIfAuthed` — a public visitor is never signed in):
```tsx
import { RequestInfo } from "./pages/RequestInfo";
// ...
<Route path="/request-info" element={<RequestInfo />} />
```

- [ ] **Step 2: Build the page**

Create `web/src/pages/RequestInfo.tsx`. It loads dropdown options, renders the Turnstile widget by injecting Cloudflare's script and calling `window.turnstile.render`, and on success swaps the form for a thank-you panel. The site key comes from `import.meta.env.VITE_TURNSTILE_SITE_KEY` (use Cloudflare's always-pass test key `1x00000000000000000000AA` locally):

```tsx
/* Public "Request Information" page — the only unauthenticated data-entry surface.
   Creates a recruiting lead via POST /intake. Protected by Cloudflare Turnstile. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError, type IntakeOptions } from "../lib/api";
import { Insignia } from "../components/Insignia";
import styles from "./RequestInfo.module.css";

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY ?? "1x00000000000000000000AA";

declare global {
  interface Window {
    turnstile?: {
      render: (el: HTMLElement, opts: { sitekey: string; callback: (t: string) => void; "error-callback"?: () => void }) => string;
      reset: (id?: string) => void;
    };
  }
}

export function RequestInfo() {
  const [options, setOptions] = useState<IntakeOptions | null>(null);
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", phone: "", current_school: "",
    grade_level: "", intended_entry_term: "fall", intended_entry_year: new Date().getFullYear() + 1,
    consent: false,
  });
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const widgetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.intakeOptions().then(setOptions).catch(() => setError("Couldn't load the form. Please refresh."));
  }, []);

  // Inject the Turnstile script once, then render the widget.
  useEffect(() => {
    const id = "cf-turnstile-script";
    function renderWidget() {
      if (window.turnstile && widgetRef.current && !widgetRef.current.hasChildNodes()) {
        window.turnstile.render(widgetRef.current, {
          sitekey: SITE_KEY,
          callback: setToken,
          "error-callback": () => setToken(""),
        });
      }
    }
    if (document.getElementById(id)) { renderWidget(); return; }
    const s = document.createElement("script");
    s.id = id;
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
    s.async = true;
    s.onload = renderWidget;
    document.head.appendChild(s);
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.consent) { setError("Please confirm you agree to be contacted."); return; }
    setBusy(true);
    try {
      await api.submitIntake({ ...form, turnstile_token: token } as never);
      setDone(true);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setError(msg);
      window.turnstile?.reset();
      setToken("");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className={styles.wrap}>
        <div className={styles.card}>
          <Insignia size={40} />
          <h1 className={styles.title}>Thank you!</h1>
          <p className={styles.lede}>We received your information. A Detachment 695 recruiter will reach out soon.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <form className={styles.card} onSubmit={onSubmit}>
        <div className={styles.head}>
          <Insignia size={40} />
          <div>
            <h1 className={styles.title}>Request Information</h1>
            <p className={styles.lede}>Interested in Air Force ROTC at Detachment 695? Tell us about yourself.</p>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.row}>
          <Field label="First name" value={form.first_name} onChange={(v) => setForm({ ...form, first_name: v })} required />
          <Field label="Last name" value={form.last_name} onChange={(v) => setForm({ ...form, last_name: v })} required />
        </div>
        <Field label="Email" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} required />
        <Field label="Phone" type="tel" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} required />
        <Field label="Current school" value={form.current_school} onChange={(v) => setForm({ ...form, current_school: v })} required />

        <div className={styles.group}>
          <label className="field-label" htmlFor="grade">Grade / year</label>
          <select id="grade" className="input" required value={form.grade_level}
                  onChange={(e) => setForm({ ...form, grade_level: e.target.value })}>
            <option value="" disabled>Select…</option>
            {options?.grade_levels.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className={styles.row}>
          <div className={styles.group}>
            <label className="field-label" htmlFor="term">Intended start term</label>
            <select id="term" className="input" value={form.intended_entry_term}
                    onChange={(e) => setForm({ ...form, intended_entry_term: e.target.value })}>
              {options?.terms.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className={styles.group}>
            <label className="field-label" htmlFor="year">Year</label>
            <input id="year" className="input" type="number" min={2000} max={2100} value={form.intended_entry_year}
                   onChange={(e) => setForm({ ...form, intended_entry_year: Number(e.target.value) })} required />
          </div>
        </div>

        <label className={styles.consent}>
          <input type="checkbox" checked={form.consent}
                 onChange={(e) => setForm({ ...form, consent: e.target.checked })} />
          <span>I agree to be contacted by phone, text, or email about AFROTC Detachment 695.</span>
        </label>

        <div ref={widgetRef} className={styles.turnstile} />

        <button className={`btn btn-primary ${styles.submit}`} type="submit" disabled={busy}>
          {busy ? "Submitting…" : "Submit"}
        </button>
      </form>
    </div>
  );
}

function Field(props: { label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean }) {
  const id = props.label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={styles.group}>
      <label className="field-label" htmlFor={id}>{props.label}</label>
      <input id={id} className="input" type={props.type ?? "text"} value={props.value}
             required={props.required} onChange={(e) => props.onChange(e.target.value)} />
    </div>
  );
}
```

- [ ] **Step 3: Add minimal styles**

Create `web/src/pages/RequestInfo.module.css` (mirror the visual tokens used elsewhere — `var(--...)` custom properties already defined in `index.css`):

```css
.wrap { min-height: 100vh; display: grid; place-items: center; padding: 2rem 1rem; background: var(--bg, #0b1220); }
.card { width: 100%; max-width: 560px; background: var(--panel, #121a2b); border: 1px solid var(--border, #223); border-radius: 14px; padding: 2rem; display: flex; flex-direction: column; gap: 1rem; }
.head { display: flex; gap: 1rem; align-items: center; }
.title { margin: 0; font-size: 1.5rem; }
.lede { margin: .25rem 0 0; color: var(--muted, #9fb0c9); font-size: .95rem; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.group { display: flex; flex-direction: column; gap: .35rem; }
.consent { display: flex; gap: .6rem; align-items: flex-start; font-size: .9rem; color: var(--muted, #9fb0c9); }
.turnstile { min-height: 65px; }
.submit { margin-top: .5rem; }
.error { background: #3a1620; border: 1px solid #7a2740; color: #ffb3c1; padding: .6rem .8rem; border-radius: 8px; font-size: .9rem; }
@media (max-width: 520px) { .row { grid-template-columns: 1fr; } }
```

- [ ] **Step 4: Build and manually verify**

Run: `cd web && npm run build`
Expected: build succeeds. Then `npm run dev`, open `/request-info` in the browser: the form renders, the dropdowns populate, the Turnstile test widget shows and auto-passes, and a submit produces the thank-you panel. Confirm the backend created a `PotentialRecruit` row (`stage=lead`, `source=public_intake_form`). (Backend must be running locally with a Neon `DATABASE_URL`; Turnstile/Resend can stay unset — dev mode.)

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/RequestInfo.tsx web/src/pages/RequestInfo.module.css web/src/main.tsx
git commit -m "feat(intake): public /request-info page with Turnstile widget"
```

---

## Task 10: Admin "Request-Info Settings" panel (web)

**Files:**
- Modify: `web/src/pages/Admin.tsx`
- Modify: `web/src/pages/Admin.module.css`

**Interfaces:**
- Consumes: `api.getIntakeSettings()`, `api.updateIntakeSettings()`, types from Task 8.
- Produces: a third section in the Admin console for editing recruiter email + ack template.

- [ ] **Step 1: Add a settings section**

In `web/src/pages/Admin.tsx`, add a new panel/tab (follow the file's existing tab/section pattern — read the current structure first). The panel:
- Loads settings with `useQuery(["intake-settings"], api.getIntakeSettings)`.
- Renders an email input (`recruiter_notification_email`), a subject input (`ack_email_subject`), and a `<textarea>` for `ack_email_body`, plus a helper line: "Use `{{first_name}}` to personalize. Links are clickable in the email.".
- Saves via `useMutation` calling `api.updateIntakeSettings(...)`, invalidating `["intake-settings"]` on success, with an inline success/error line (mirror how the Users panel surfaces mutation results).

Add the corresponding type import at the top:
```ts
type IntakeSettingsOut = components["schemas"]["IntakeSettingsOut"];
```

- [ ] **Step 2: Add styles as needed**

In `web/src/pages/Admin.module.css`, add a `.templateArea` rule (`width: 100%; min-height: 180px; font-family: inherit;`) and reuse existing form/section classes.

- [ ] **Step 3: Build + manual verify**

Run: `cd web && npm run build`, then `npm run dev`. Sign in as admin, open the new settings section, change the recruiter email + subject, save, reload — the values persist. Confirm a non-admin (recruiter) never sees the section (the whole Admin screen is already admin-gated).

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/Admin.tsx web/src/pages/Admin.module.css
git commit -m "feat(intake): admin Request-Info Settings panel (recruiter email + ack template)"
```

---

## Task 11: CSV download button on Recruits (web)

**Files:**
- Modify: `web/src/pages/Recruits.tsx`

**Interfaces:**
- Consumes: existing `GET /export/recruits?format=csv` (already implemented in `backend/app/api/v1/exports.py`) via `api.raw(...)`.

- [ ] **Step 1: Add a download handler + button**

In `web/src/pages/Recruits.tsx`, add a "Download CSV" button in the page header. Handler downloads the authenticated file blob and triggers a save:
```tsx
async function downloadCsv() {
  const res = await api.raw("/export/recruits?format=csv");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "recruits.csv";
  a.click();
  URL.revokeObjectURL(url);
}
```
(`api.raw` returns the raw `Response` with the bearer token attached — see `web/src/lib/api.ts`.)

- [ ] **Step 2: Build + manual verify**

Run: `cd web && npm run build`, then in `npm run dev` click "Download CSV" on the Recruits page — a `recruits.csv` downloads with the expected columns.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Recruits.tsx
git commit -m "feat(recruits): expose CSV download button (wires existing export endpoint)"
```

---

## Task 12: iOS admin settings parity

**Files:**
- Modify: `ios/Det695/Models/Admin.swift`
- Modify: `ios/Det695/Networking/APIClient.swift`
- Modify: `ios/Det695/Views/AdminView.swift`

**Interfaces:**
- Consumes: `GET/PUT /admin/intake-settings`.
- Produces: `IntakeSettingsOut`/`IntakeSettingsUpdate` Swift models; `APIClient.intakeSettings()` / `updateIntakeSettings(_:)`; a "Settings" segment in `AdminConsole`.

- [ ] **Step 1: Add the models**

In `ios/Det695/Models/Admin.swift`, append:
```swift
/// GET /admin/intake-settings — decoded with .convertFromSnakeCase.
struct IntakeSettingsOut: Decodable {
    let id: Int
    var recruiterNotificationEmail: String?
    let ackEmailSubject: String
    let ackEmailBody: String
}

/// PUT /admin/intake-settings — only sent keys change (backend exclude_unset).
struct IntakeSettingsUpdate: Encodable {
    var recruiterNotificationEmail: String?
    var ackEmailSubject: String?
    var ackEmailBody: String?
}
```

- [ ] **Step 2: Add the API methods**

In `ios/Det695/Networking/APIClient.swift`, next to the other `/admin` methods:
```swift
func intakeSettings() async throws -> IntakeSettingsOut {
    try await requestJSON("/admin/intake-settings", method: "GET", bodyData: nil, authed: true)
}

@discardableResult
func updateIntakeSettings(_ body: IntakeSettingsUpdate) async throws -> IntakeSettingsOut {
    try await requestJSON("/admin/intake-settings", method: "PUT",
                          bodyData: try encoder.encode(body), authed: true)
}
```

- [ ] **Step 3: Add a Settings segment to `AdminConsole`**

In `ios/Det695/Views/AdminView.swift`:
- Extend the `Tab` enum: `case users, activity, settings` (label for `.settings` → "Settings").
- Add a `case .settings: IntakeSettingsPanel()` branch in the `switch tab`.
- Add a `private struct IntakeSettingsPanel: View` that loads via `.task { settings = try await APIClient.shared.intakeSettings() }` (match how other panels obtain the client — read the file for the exact accessor, e.g. `APIClient.shared` or an injected instance), shows a `Form` with a `TextField` for the recruiter email, a `TextField` for subject, a `TextEditor` for the body (with a footnote "Use {{first_name}} to personalize"), and a Save button calling `updateIntakeSettings(...)` with an inline status line — mirroring the existing panels' loading/error/inline-status conventions.

- [ ] **Step 4: Build**

Run: `cd ios && xcodegen generate && xcodebuild -scheme Det695 -destination 'generic/platform=iOS Simulator' build`
Expected: build succeeds. Then launch in the simulator (autologin as admin), open More → Admin → Settings, confirm the values load, edit + save, and re-open to confirm persistence. (Follow this repo's existing iOS build-and-drive verification convention.)

- [ ] **Step 5: Commit**

```bash
git add ios/Det695/Models/Admin.swift ios/Det695/Networking/APIClient.swift ios/Det695/Views/AdminView.swift
git commit -m "feat(intake): iOS admin Request-Info Settings parity"
```

---

## Task 13: Rollout — migrate Neon, verify backups, wire Resend + Turnstile

**Files:** none (operational). Produces a working, deployed feature.

- [ ] **Step 1: Apply the migration to Neon**

Against the **direct, non-pooled** Neon host (per `backend/README.md`):
```bash
cd backend && uv run alembic upgrade head
```
Confirm with `uv run alembic current` that head matches the new revision.

- [ ] **Step 2: Verify the backup/restore drill against the new schema (per spec + user request)**

Trigger a fresh backup, then the restore drill (both from the Actions tab or via `gh workflow run`, per `BACKUP.md`):
```bash
gh workflow run backup.yml --repo drewdog88/afrotc-native-ios
# wait for it to finish, then:
gh workflow run restore-drill.yml --repo drewdog88/afrotc-native-ios
```
Confirm the restore-drill run is **green** and its Summary lists the new `intake_settings` table with a row count, and `potential_recruit` restores with its new columns. If red, STOP and investigate before considering the feature done.

- [ ] **Step 3: Verify Resend sending domain + set env**

In Resend: verify a sending domain (add the DNS records Resend provides) and pick a from-address on it. Then set the production env (Vercel project settings):
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL` (an address on the verified domain)

- [ ] **Step 4: Create the Turnstile widget + set keys**

Create a Turnstile widget in Cloudflare (scripted via the Cloudflare API/CLI where possible; otherwise the dashboard) for the production hostname. Set:
- `TURNSTILE_SECRET_KEY` (backend env, Vercel)
- `VITE_TURNSTILE_SITE_KEY` (web build env, Vercel) — the public site key

- [ ] **Step 5: Deploy + end-to-end smoke test**

Deploy. On the live site: open `/request-info`, confirm the Turnstile widget renders (proves the CSP change shipped), submit a real test inquiry, and confirm (a) a `PotentialRecruit` lead appears, (b) the applicant acknowledgment email arrives, and (c) the recruiter notification arrives at the configured address. Then delete the test lead.

- [ ] **Step 6: Commit any doc updates**

If you update `README.md`/`BACKUP.md`/`docs` to mention the new public route and env vars, commit them:
```bash
git add -A && git commit -m "docs(intake): document /request-info route and Resend/Turnstile env vars"
```

---

## Self-Review

**Spec coverage:**
- Public unauthenticated form → Tasks 5, 9. ✓
- Creates `PotentialRecruit` at `stage=LEAD` (no new "opportunities" table) → Task 5. ✓
- Recruiter notification email → Tasks 3, 5. ✓
- Applicant acknowledgment with admin-editable template → Tasks 3, 5, 6, 10, 12. ✓
- Admin-configurable recruiter email + template, web + iOS parity → Tasks 6, 10, 12. ✓
- Turnstile + rate-limit backstop → Task 4, 8 (CSP), 9 (widget), 13 (keys). ✓
- Data model: grade_level, intended term/year, consent, source, source_ip, acknowledgment stamp, `SchoolType.OTHER` → Task 1. ✓
- Plain-text ack email (injection-safe) → Task 3. ✓
- `OTHER` grade → `SchoolType.OTHER`, not college → Tasks 1, 5 (test). ✓
- CSV download button → Task 11. ✓
- CSP allowance for Turnstile → Task 8. ✓
- Resend verified-domain prerequisite → Task 13. ✓
- Backup/restore drill after schema change → Task 13. ✓
- iOS: admin settings only, no public form → Task 12 (form absent by omission). ✓
- Contract regeneration → Task 7. ✓

**Placeholder scan:** No "TBD"/"add validation"/"similar to Task N". Each code step has concrete content. Task 10 (web) and Task 12 (iOS) reference "the file's existing pattern" for UI-panel wiring rather than transcribing full panels — deliberate, since they must match large existing components read at execution time; the data flow, endpoints, types, and helper text are all specified.

**Type consistency:** `IntakeCreate`, `IntakeSubmitResult`, `IntakeOptions`, `IntakeSettingsOut`, `IntakeSettingsUpdate` used identically across backend schemas (Tasks 5–6), generated types (Task 7), web client (Task 8), and iOS models (Task 12). `school_type_for_grade` defined in Task 1, consumed in Task 5. `send_email`/`verify_turnstile` imported at module scope in `intake.py` so tests monkeypatch them (Task 5 tests match). `source="public_intake_form"` string is consistent between the router (Task 5) and its test assertion. Rate-limit constant `RATE_LIMIT_PER_HOUR = 30` matches the spec's loose backstop.
