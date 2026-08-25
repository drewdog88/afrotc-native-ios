# Email 2FA — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in email one-time-code 2FA (with first-login enrollment, admin enforcement, dedicated verify step, and 30-day trusted devices) to the FastAPI backend, on a method-based scaffold that leaves TOTP dormant for the future.

**Architecture:** 2FA is modeled as a *method* on the user (`email` active, `totp` reserved). A shared OTP service issues/verifies short-lived codes stored hashed on the user row; a trusted-device service issues opaque tokens (sha256-hashed, looked up by hash) that let a device skip the code for 30 days. Login becomes a two-step flow — password → email challenge (`challenge_token`) → code verify → tokens — with a trusted-device pre-check that skips the challenge. Profile and admin routers gain enroll/verify/disable and per-user enable + trusted-device management.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (`Mapped`/`mapped_column`), Alembic, Pydantic v2, `bcrypt` (code hashing, reused from `security.py`), `hashlib.sha256` (opaque device tokens), Resend (`app/services/email.py`), pytest + SQLite in-memory harness.

**Spec:** `docs/superpowers/specs/2026-08-25-email-2fa-design.md`

## Global Constraints

- Python 3.11; run everything with `uv run` (e.g. `uv run pytest`). Work in `backend/`.
- Postgres-only at runtime — no local/SQLite fallback in app code. Tests use the SQLite harness in `backend/tests/conftest.py`.
- Codes and device tokens are **never stored in plaintext**: OTP codes → `bcrypt` via `security.hash_password`/`verify_password`; device tokens → `security.hash_token` (sha256 hex, added in Task 1).
- New service/router modules that need the current time MUST use `from app.core import security` and call `security.now_utc()` (attribute access), NOT `from app.core.security import now_utc`. The test harness monkeypatches `security.now_utc`; attribute access picks that up with no conftest change.
- Email sends are best-effort (`send_email` returns `bool`, never raises). A failed send never turns a login into a 500.
- Code policy (from spec, exact values): code length **6**, TTL **10** minutes, max verify attempts **5**, resend cooldown **60** seconds, max resends **3**, trusted-device TTL **30** days.
- Follow existing patterns: routers under `app/api/v1/`, schemas under `app/schemas/`, one commit per task (Conventional Commits, `feat:`/`test:`/`chore:`).
- The existing authenticator-TOTP *endpoints and tests* are replaced by the email flow; the TOTP *columns* stay (dormant). Do not drop `totp_*` columns.

---

### Task 1: Config settings + security helpers

**Files:**
- Modify: `backend/app/core/config.py` (add settings after the Email block, ~line 66)
- Modify: `backend/app/core/security.py` (add helpers)
- Test: `backend/tests/test_security_helpers.py` (create)

**Interfaces:**
- Produces:
  - `settings.otp_code_length: int`, `otp_ttl_minutes: int`, `otp_max_attempts: int`, `otp_resend_cooldown_seconds: int`, `otp_max_resends: int`, `trusted_device_ttl_days: int`, `trusted_device_cookie_name: str`
  - `security.hash_token(token: str) -> str` (sha256 hex)
  - `security.create_challenge_token(subject: str) -> str` (JWT, `type="login_2fa"`, expires in `otp_ttl_minutes`)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_security_helpers.py
from app.core import security
from app.core.config import settings


def test_hash_token_is_deterministic_sha256_hex() -> None:
    h1 = security.hash_token("abc123")
    h2 = security.hash_token("abc123")
    assert h1 == h2
    assert len(h1) == 64 and all(c in "0123456789abcdef" for c in h1)
    assert security.hash_token("different") != h1


def test_challenge_token_roundtrips_with_type() -> None:
    token = security.create_challenge_token("42")
    payload = security.decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["type"] == "login_2fa"


def test_2fa_settings_defaults() -> None:
    assert settings.otp_code_length == 6
    assert settings.otp_ttl_minutes == 10
    assert settings.otp_max_attempts == 5
    assert settings.otp_resend_cooldown_seconds == 60
    assert settings.otp_max_resends == 3
    assert settings.trusted_device_ttl_days == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_security_helpers.py -v`
Expected: FAIL (`AttributeError: module 'app.core.security' has no attribute 'hash_token'`).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/core/config.py`, add inside `Settings` (after the `resend_from_email` line):

```python
    # 2FA — email one-time code
    otp_code_length: int = 6
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_resends: int = 3

    # Trusted devices (skip the 2FA code on a known device)
    trusted_device_ttl_days: int = 30
    trusted_device_cookie_name: str = "det695_trust"
```

In `backend/app/core/security.py`, add `import hashlib` at the top (with the other imports) and append:

```python
# ---- Opaque-token hashing (trusted devices) ----
def hash_token(token: str) -> str:
    """Deterministic sha256 hex of a high-entropy token, for indexed lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---- 2FA login challenge token ----
def create_challenge_token(subject: str) -> str:
    """Short-lived signed token proving 'password step passed, code pending'."""
    return _create_token(
        subject, "login_2fa", timedelta(minutes=settings.otp_ttl_minutes)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_security_helpers.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/core/security.py backend/tests/test_security_helpers.py
git commit -m "feat: 2FA config settings + challenge-token and token-hash helpers"
```

---

### Task 2: User model 2FA columns + `is_2fa_active` + test factory

**Files:**
- Modify: `backend/app/models/user.py` (add columns near the existing `# 2FA (TOTP)` block ~line 41-46; update `is_2fa_active` ~line 72-73)
- Modify: `backend/tests/conftest.py` (extend `make_user` factory)
- Test: `backend/tests/test_user_2fa_model.py` (create)

**Interfaces:**
- Produces on `User`:
  - `two_factor_method: str | None`, `two_factor_enabled: bool`, `two_factor_enrollment_prompted: bool`
  - `otp_code_hash: str | None`, `otp_expires_at: datetime | None`, `otp_attempts: int`, `otp_resends: int`, `otp_purpose: str | None`, `otp_last_sent_at: datetime | None`
  - `is_2fa_active` property → `two_factor_enabled and two_factor_method is not None`
  - `make_user(..., two_factor_method=None, two_factor_enabled=False, two_factor_enrollment_prompted=False)`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_user_2fa_model.py
from collections.abc import Callable

from app.models import User


def test_is_2fa_active_requires_enabled_and_method(make_user: Callable[..., User]) -> None:
    off = make_user("noa")
    assert off.is_2fa_active is False

    enabled_no_method = make_user("bad", two_factor_enabled=True)
    assert enabled_no_method.is_2fa_active is False

    active = make_user("good", two_factor_enabled=True, two_factor_method="email")
    assert active.is_2fa_active is True


def test_new_2fa_columns_default(make_user: Callable[..., User]) -> None:
    u = make_user("fresh")
    assert u.two_factor_method is None
    assert u.two_factor_enabled is False
    assert u.two_factor_enrollment_prompted is False
    assert u.otp_code_hash is None
    assert u.otp_attempts == 0
    assert u.otp_resends == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_user_2fa_model.py -v`
Expected: FAIL (`TypeError: _make() got an unexpected keyword argument 'two_factor_enabled'`).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/models/user.py`, add after the existing `can_enable_2fa` column (~line 46):

```python

    # Generic method-based 2FA. `email` is the only active method today;
    # `totp` (the columns above) is reserved for the future and reuses the
    # same enable/challenge/verify/admin/trust plumbing.
    two_factor_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_enrollment_prompted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pending one-time code (email method) — used for enrollment and login.
    otp_code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    otp_resends: Mapped[int] = mapped_column(Integer, default=0)
    otp_purpose: Mapped[str | None] = mapped_column(String(20), nullable=True)
    otp_last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Replace the existing `is_2fa_active` property body (~line 72-73):

```python
    @property
    def is_2fa_active(self) -> bool:
        return self.two_factor_enabled and self.two_factor_method is not None
```

In `backend/tests/conftest.py`, extend `_make` in the `make_user` fixture — add these keyword params to the signature (after `totp_setup_completed`):

```python
        two_factor_method: str | None = None,
        two_factor_enabled: bool = False,
        two_factor_enrollment_prompted: bool = False,
```

and pass them into the `User(...)` constructor (after `totp_setup_completed=totp_setup_completed,`):

```python
                two_factor_method=two_factor_method,
                two_factor_enabled=two_factor_enabled,
                two_factor_enrollment_prompted=two_factor_enrollment_prompted,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_user_2fa_model.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/user.py backend/tests/conftest.py backend/tests/test_user_2fa_model.py
git commit -m "feat: method-based 2FA columns on User + is_2fa_active"
```

---

### Task 3: TrustedDevice model

**Files:**
- Create: `backend/app/models/trusted_device.py`
- Modify: `backend/app/models/__init__.py` (import + `__all__`)
- Test: `backend/tests/test_trusted_device_model.py` (create)

**Interfaces:**
- Produces: `TrustedDevice(id, user_id, token_hash, device_label, created_at, last_used_at, expires_at, revoked_at)` importable via `from app.models import TrustedDevice`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_trusted_device_model.py
from collections.abc import Callable
from datetime import datetime, timedelta

from app.models import TrustedDevice, User
from tests.conftest import TestingSessionLocal


def test_trusted_device_persists(make_user: Callable[..., User]) -> None:
    user = make_user("dev")
    now = datetime.now().replace(microsecond=0)
    with TestingSessionLocal() as db:
        db.add(TrustedDevice(
            user_id=user.id, token_hash="a" * 64, device_label="iPhone",
            created_at=now, last_used_at=now, expires_at=now + timedelta(days=30),
        ))
        db.commit()
        row = db.query(TrustedDevice).one()
        assert row.user_id == user.id
        assert row.revoked_at is None
        assert row.device_label == "iPhone"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_trusted_device_model.py -v`
Expected: FAIL (`ImportError: cannot import name 'TrustedDevice'`).

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/models/trusted_device.py`:

```python
"""Trusted devices — a device that has cleared 2FA may skip the code for a while."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), index=True)  # sha256 hex
    device_label: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

In `backend/app/models/__init__.py`, add the import (with the others) and the name to `__all__`:

```python
from app.models.trusted_device import TrustedDevice
```
```python
    "TrustedDevice",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_trusted_device_model.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/trusted_device.py backend/app/models/__init__.py backend/tests/test_trusted_device_model.py
git commit -m "feat: TrustedDevice model"
```

---

### Task 4: Alembic migration (additive)

**Files:**
- Create: `backend/alembic/versions/<generated>_email_2fa_and_trusted_devices.py`

**Interfaces:**
- Consumes: the new columns/table from Tasks 2-3.
- Produces: a forward + reverse migration that adds the `users` 2FA columns and creates `trusted_devices`. Additive and backward-compatible; no data backfill.

- [ ] **Step 1: Find the current head**

Run: `cd backend && uv run alembic heads`
Note the revision id printed — it is the `down_revision` for the new migration.

- [ ] **Step 2: Create the migration file**

Create `backend/alembic/versions/2026_08_25_email_2fa.py` (filename is fine; revision id is what matters):

```python
"""email 2FA + trusted devices

Additive: new nullable/defaulted columns on users + a trusted_devices table.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers.
revision = "email2fa0001"
down_revision = "REPLACE_WITH_OUTPUT_OF_ALEMBIC_HEADS"  # set from Step 1
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("two_factor_method", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("two_factor_enrollment_prompted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("otp_code_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("otp_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("otp_resends", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("otp_purpose", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("otp_last_sent_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "trusted_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("device_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("trusted_devices")
    for col in (
        "otp_last_sent_at", "otp_purpose", "otp_resends", "otp_attempts",
        "otp_expires_at", "otp_code_hash", "two_factor_enrollment_prompted",
        "two_factor_enabled", "two_factor_method",
    ):
        op.drop_column("users", col)
```

Set `down_revision` to the id from Step 1.

- [ ] **Step 3: Verify the migration graph is linear**

Run: `cd backend && uv run alembic heads`
Expected: a single head — `email2fa0001` (no branch). If two heads appear, the `down_revision` is wrong; fix it.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/2026_08_25_email_2fa.py
git commit -m "chore: alembic migration for email 2FA + trusted devices"
```

> Note: applying the migration (`alembic upgrade head`) runs against Postgres and is a deploy step, not part of the test suite (tests build the schema from models via SQLite).

---

### Task 5: OTP service

**Files:**
- Create: `backend/app/services/otp.py`
- Test: `backend/tests/test_otp_service.py` (create)

**Interfaces:**
- Consumes: `security.hash_password`/`verify_password`/`now_utc`, `settings.*`, `User`.
- Produces:
  - `generate_code() -> str`
  - `issue_code(user: User, purpose: str) -> str` — set fresh code (hash+expiry), reset attempts + resends
  - `resend_code(user: User) -> str | None` — new code honoring cooldown + max resends; `None` if not allowed
  - `verify_code(user: User, code: str, purpose: str) -> bool` — checks purpose/expiry/attempts; increments on fail; clears on success or exhaustion
  - `can_resend(user: User) -> bool`
  - `clear_code(user: User) -> None`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_otp_service.py
from collections.abc import Callable
from datetime import timedelta

from app.core import security
from app.models import User
from app.services import otp
from tests.conftest import TestingSessionLocal


def _persist(user: User) -> User:
    with TestingSessionLocal() as db:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def test_issue_and_verify_success(make_user: Callable[..., User]) -> None:
    user = make_user("otp1")
    code = otp.issue_code(user, "login")
    assert len(code) == 6 and code.isdigit()
    assert otp.verify_code(user, code, "login") is True
    # Cleared after success.
    assert user.otp_code_hash is None


def test_wrong_code_increments_and_caps(make_user: Callable[..., User]) -> None:
    user = make_user("otp2")
    otp.issue_code(user, "login")
    for _ in range(4):
        assert otp.verify_code(user, "000000", "login") is False
    assert user.otp_attempts == 4
    # 5th wrong attempt hits the cap and clears the challenge.
    assert otp.verify_code(user, "000000", "login") is False
    assert user.otp_code_hash is None


def test_expired_code_rejected(make_user: Callable[..., User]) -> None:
    user = make_user("otp3")
    code = otp.issue_code(user, "login")
    user.otp_expires_at = security.now_utc() - timedelta(seconds=1)
    assert otp.verify_code(user, code, "login") is False


def test_purpose_mismatch_rejected(make_user: Callable[..., User]) -> None:
    user = make_user("otp4")
    code = otp.issue_code(user, "enroll")
    assert otp.verify_code(user, code, "login") is False


def test_resend_honors_cap(make_user: Callable[..., User]) -> None:
    user = make_user("otp5")
    otp.issue_code(user, "login")
    # Force cooldown to pass each time.
    for _ in range(3):
        user.otp_last_sent_at = security.now_utc() - timedelta(seconds=61)
        assert otp.resend_code(user) is not None
    user.otp_last_sent_at = security.now_utc() - timedelta(seconds=61)
    assert otp.resend_code(user) is None  # 4th resend blocked by cap
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_otp_service.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.services.otp'`).

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/otp.py`:

```python
"""Email one-time-code lifecycle, shared by enrollment and login challenges.

The pending code lives on the user row (hashed). Callers mutate the user and
commit through their own DB session; this module never commits.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from app.core import security
from app.core.config import settings
from app.models import User


def generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(settings.otp_code_length))


def _set_code(user: User, purpose: str) -> str:
    code = generate_code()
    user.otp_code_hash = security.hash_password(code)
    user.otp_expires_at = security.now_utc() + timedelta(minutes=settings.otp_ttl_minutes)
    user.otp_attempts = 0
    user.otp_purpose = purpose
    user.otp_last_sent_at = security.now_utc()
    return code


def issue_code(user: User, purpose: str) -> str:
    """Start a fresh challenge for `purpose` (resets the resend counter)."""
    user.otp_resends = 0
    return _set_code(user, purpose)


def can_resend(user: User) -> bool:
    if user.otp_last_sent_at is None:
        return True
    elapsed = (security.now_utc() - user.otp_last_sent_at).total_seconds()
    return elapsed >= settings.otp_resend_cooldown_seconds


def resend_code(user: User) -> str | None:
    """Issue a new code for the current purpose, or None if capped / cooling down."""
    if user.otp_code_hash is None or user.otp_purpose is None:
        return None
    if user.otp_resends >= settings.otp_max_resends or not can_resend(user):
        return None
    purpose = user.otp_purpose
    resends = user.otp_resends + 1
    code = _set_code(user, purpose)
    user.otp_resends = resends
    return code


def clear_code(user: User) -> None:
    user.otp_code_hash = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    user.otp_resends = 0
    user.otp_purpose = None
    user.otp_last_sent_at = None


def verify_code(user: User, code: str, purpose: str) -> bool:
    if (
        user.otp_code_hash is None
        or user.otp_purpose != purpose
        or user.otp_expires_at is None
        or security.now_utc() > user.otp_expires_at
    ):
        return False
    if user.otp_attempts >= settings.otp_max_attempts:
        clear_code(user)
        return False
    if not security.verify_password(code, user.otp_code_hash):
        user.otp_attempts += 1
        if user.otp_attempts >= settings.otp_max_attempts:
            clear_code(user)
        return False
    clear_code(user)
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_otp_service.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/otp.py backend/tests/test_otp_service.py
git commit -m "feat: OTP code service (issue/resend/verify with caps + expiry)"
```

---

### Task 6: Trusted-device service

**Files:**
- Create: `backend/app/services/trusted_devices.py`
- Test: `backend/tests/test_trusted_devices_service.py` (create)

**Interfaces:**
- Consumes: `security.hash_token`/`now_utc`, `settings.trusted_device_ttl_days`, `TrustedDevice`, `User`.
- Produces (all commit their own session writes):
  - `trust_device(db, user, label) -> str` (plaintext token; hash stored)
  - `find_valid(db, user, token: str | None) -> TrustedDevice | None` (touches `last_used_at`)
  - `list_devices(db, user) -> list[TrustedDevice]`
  - `revoke(db, user, device_id: int) -> bool`
  - `revoke_all(db, user, except_token: str | None = None) -> int`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_trusted_devices_service.py
from collections.abc import Callable
from datetime import timedelta

from app.core import security
from app.models import TrustedDevice, User
from app.services import trusted_devices as td
from tests.conftest import TestingSessionLocal


def test_trust_then_find(make_user: Callable[..., User]) -> None:
    user = make_user("td1")
    with TestingSessionLocal() as db:
        token = td.trust_device(db, user, "iPhone 15")
        found = td.find_valid(db, user, token)
        assert found is not None and found.device_label == "iPhone 15"
        assert td.find_valid(db, user, "bogus") is None


def test_expired_is_not_valid(make_user: Callable[..., User]) -> None:
    user = make_user("td2")
    with TestingSessionLocal() as db:
        token = td.trust_device(db, user, "old")
        row = db.query(TrustedDevice).one()
        row.expires_at = security.now_utc() - timedelta(days=1)
        db.commit()
        assert td.find_valid(db, user, token) is None


def test_revoke_all_except_current(make_user: Callable[..., User]) -> None:
    user = make_user("td3")
    with TestingSessionLocal() as db:
        keep = td.trust_device(db, user, "this")
        td.trust_device(db, user, "other-a")
        td.trust_device(db, user, "other-b")
        n = td.revoke_all(db, user, except_token=keep)
        assert n == 2
        assert td.find_valid(db, user, keep) is not None
        assert len(td.list_devices(db, user)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_trusted_devices_service.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.services.trusted_devices'`).

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/trusted_devices.py`:

```python
"""Trusted-device tokens: a device that cleared 2FA may skip the code for a while."""
from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models import User
from app.models.trusted_device import TrustedDevice


def trust_device(db: Session, user: User, label: str) -> str:
    token = secrets.token_urlsafe(32)
    now = security.now_utc()
    db.add(
        TrustedDevice(
            user_id=user.id,
            token_hash=security.hash_token(token),
            device_label=(label or "")[:255],
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(days=settings.trusted_device_ttl_days),
        )
    )
    db.commit()
    return token


def find_valid(db: Session, user: User, token: str | None) -> TrustedDevice | None:
    if not token:
        return None
    row = db.scalar(
        select(TrustedDevice).where(
            TrustedDevice.user_id == user.id,
            TrustedDevice.token_hash == security.hash_token(token),
            TrustedDevice.revoked_at.is_(None),
        )
    )
    if row is None or row.expires_at <= security.now_utc():
        return None
    row.last_used_at = security.now_utc()
    db.commit()
    return row


def list_devices(db: Session, user: User) -> list[TrustedDevice]:
    return list(
        db.scalars(
            select(TrustedDevice)
            .where(TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None))
            .order_by(TrustedDevice.last_used_at.desc())
        )
    )


def revoke(db: Session, user: User, device_id: int) -> bool:
    row = db.get(TrustedDevice, device_id)
    if row is None or row.user_id != user.id or row.revoked_at is not None:
        return False
    row.revoked_at = security.now_utc()
    db.commit()
    return True


def revoke_all(db: Session, user: User, except_token: str | None = None) -> int:
    keep = security.hash_token(except_token) if except_token else None
    rows = db.scalars(
        select(TrustedDevice).where(
            TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None)
        )
    ).all()
    now = security.now_utc()
    count = 0
    for row in rows:
        if keep and row.token_hash == keep:
            continue
        row.revoked_at = now
        count += 1
    db.commit()
    return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_trusted_devices_service.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/trusted_devices.py backend/tests/test_trusted_devices_service.py
git commit -m "feat: trusted-device service (trust/find/list/revoke)"
```

---

### Task 7: 2FA code email

**Files:**
- Modify: `backend/app/services/email.py` (add builder + sender)
- Test: `backend/tests/test_2fa_email.py` (create)

**Interfaces:**
- Produces:
  - `build_2fa_code_email(code: str) -> tuple[str, str]` (subject, body)
  - `send_2fa_code(to: str, code: str) -> bool` (delegates to `send_email`)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_2fa_email.py
import app.services.email as email


def test_build_2fa_code_email_contains_code() -> None:
    subject, body = email.build_2fa_code_email("246810")
    assert "246810" in body
    assert "code" in subject.lower()


def test_send_2fa_code_delegates(monkeypatch) -> None:
    captured = {}

    def fake_send(to, subject, body):
        captured.update(to=to, subject=subject, body=body)
        return True

    monkeypatch.setattr(email, "send_email", fake_send)
    assert email.send_2fa_code("u@example.com", "135791") is True
    assert captured["to"] == "u@example.com"
    assert "135791" in captured["body"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_2fa_email.py -v`
Expected: FAIL (`AttributeError: module 'app.services.email' has no attribute 'build_2fa_code_email'`).

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/services/email.py`:

```python
def build_2fa_code_email(code: str) -> tuple[str, str]:
    """Subject/body for a sign-in one-time code."""
    subject = "Your AFROTC Det 695 sign-in code"
    body = "\n".join(
        [
            f"Your one-time sign-in code is: {code}",
            "",
            "It expires shortly. If you didn't try to sign in, you can ignore this email.",
        ]
    )
    return subject, body


def send_2fa_code(to: str, code: str) -> bool:
    subject, body = build_2fa_code_email(code)
    return send_email(to, subject, body)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_2fa_email.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/email.py backend/tests/test_2fa_email.py
git commit -m "feat: 2FA sign-in code email template + sender"
```

---

### Task 8: Login flow — trusted pre-check, email challenge, verify, resend

**Files:**
- Modify: `backend/app/schemas/auth.py` (request/response models)
- Modify: `backend/app/api/v1/auth.py` (rewrite `login`; add `login/verify`, `login/resend`; helpers)
- Test: `backend/tests/test_2fa_login.py` (create)
- Modify: `backend/tests/test_auth.py` (replace the TOTP test `test_2fa_required_and_verified`)

**Interfaces:**
- Consumes: `otp.*`, `trusted_devices.*`, `email.send_2fa_code`, `security.create_challenge_token`, `settings.trusted_device_cookie_name`, `settings.trusted_device_ttl_days`.
- Produces:
  - `LoginRequest` gains `trust_token: str | None = None`
  - `LoginResponse{access_token?, refresh_token?, token_type, force_password_change, two_factor_required, method?, challenge_token?}`
  - `LoginVerifyRequest{challenge_token, code, trust_device}`, `LoginVerifyResponse(TokenPair){trust_token?}`
  - `ResendRequest{challenge_token}`
  - Endpoints: `POST /auth/login` → `LoginResponse`; `POST /auth/login/verify` → `LoginVerifyResponse`; `POST /auth/login/resend` → `Message`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_2fa_login.py
from collections.abc import Callable

import app.services.email as email
import app.services.otp as otp
from app.models import User
from fastapi.testclient import TestClient


def _fixed_code(monkeypatch, code: str = "123456") -> None:
    monkeypatch.setattr(otp, "generate_code", lambda: code)
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)


def _enrolled(make_user: Callable[..., User]) -> User:
    return make_user("mfa", "Recruit123!", two_factor_enabled=True, two_factor_method="email")


def test_login_with_2fa_returns_challenge_not_tokens(
    client: TestClient, make_user, login, monkeypatch
) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    resp = login(client, "mfa", "Recruit123!")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["two_factor_required"] is True
    assert body["method"] == "email"
    assert body["challenge_token"]
    assert body["access_token"] is None


def test_verify_issues_tokens(client: TestClient, make_user, login, monkeypatch) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    challenge = login(client, "mfa", "Recruit123!").json()["challenge_token"]
    resp = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_wrong_code_is_401(client: TestClient, make_user, login, monkeypatch) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    challenge = login(client, "mfa", "Recruit123!").json()["challenge_token"]
    resp = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "999999", "trust_device": False},
    )
    assert resp.status_code == 401


def test_trust_device_then_skip_code(client: TestClient, make_user, login, monkeypatch) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    challenge = login(client, "mfa", "Recruit123!").json()["challenge_token"]
    verified = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": True},
    )
    trust_token = verified.json()["trust_token"]
    assert trust_token
    # New login presenting the trust token skips the code and returns tokens.
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "mfa", "password": "Recruit123!", "trust_token": trust_token},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json().get("two_factor_required", False) is False


def test_no_2fa_login_still_returns_tokens(client: TestClient, make_user, login) -> None:
    make_user("plain", "Recruit123!")
    resp = login(client, "plain", "Recruit123!")
    assert resp.status_code == 200
    assert resp.json()["access_token"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_2fa_login.py -v`
Expected: FAIL (verify endpoint 404 / `two_factor_required` KeyError).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas/auth.py`: add `trust_token` to `LoginRequest` and add the new models (import `Message` is not needed here — the resend endpoint returns `app.schemas.common.Message`):

```python
class LoginRequest(BaseModel):
    username: str  # accepts username or email
    password: str
    totp_code: str | None = None  # legacy; unused by the email flow, kept for compat
    trust_token: str | None = None  # opaque trusted-device token (also read from cookie)


class LoginResponse(BaseModel):
    """Either a token pair (success) or a 2FA challenge that needs a code."""
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    force_password_change: bool = False
    two_factor_required: bool = False
    method: str | None = None
    challenge_token: str | None = None


class LoginVerifyRequest(BaseModel):
    challenge_token: str
    code: str
    trust_device: bool = False


class LoginVerifyResponse(TokenPair):
    trust_token: str | None = None


class ResendRequest(BaseModel):
    challenge_token: str
```

In `backend/app/api/v1/auth.py`: update imports and rewrite the login section. Replace the import block for services/schemas and add:

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.core.security import create_challenge_token
from app.services import otp, trusted_devices
from app.services.email import send_2fa_code
from app.schemas.auth import (
    AccessToken, ForgotPasswordRequest, LoginRequest, LoginResponse,
    LoginVerifyRequest, LoginVerifyResponse, PasswordChange, RefreshRequest,
    ResendRequest, ResetPasswordRequest, SecretQuestionOut, TokenPair, UserOut,
)
from app.schemas.common import Message
```

Remove `import pyotp` and the `decrypt_secret` import (no longer used by login). Replace the `login` function (lines ~81-132) with:

```python
def _issue_token_pair(user: User) -> tuple[str, str]:
    subject = str(user.id)
    return create_access_token(subject), create_refresh_token(subject)


def _record_login(db: Session, user: User, request: Request) -> None:
    user.failed_login_attempts = 0
    db.commit()
    record_activity(
        db, user=user, action="LOGIN", table_name="users",
        record_id=user.id, record_description=user.username, request=request,
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    user = _find_user(db, body.username)
    if user is None:
        raise _BAD_CREDS
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked due to failed logins. Contact an administrator.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    if not verify_password(body.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.is_locked = True
        db.commit()
        raise _BAD_CREDS

    if user.is_2fa_active:
        cookie_token = request.cookies.get(settings.trusted_device_cookie_name)
        if trusted_devices.find_valid(db, user, body.trust_token or cookie_token):
            _record_login(db, user, request)
            access, refresh = _issue_token_pair(user)
            return LoginResponse(
                access_token=access, refresh_token=refresh,
                force_password_change=user.force_password_change or user.is_password_expired,
            )
        # Email challenge: mint + store a code, email it, return a challenge token.
        code = otp.issue_code(user, "login")
        db.commit()
        send_2fa_code(user.email, code)
        return LoginResponse(
            two_factor_required=True,
            method=user.two_factor_method,
            challenge_token=create_challenge_token(str(user.id)),
        )

    _record_login(db, user, request)
    access, refresh = _issue_token_pair(user)
    return LoginResponse(
        access_token=access, refresh_token=refresh,
        force_password_change=user.force_password_change or user.is_password_expired,
    )


def _challenge_user(db: Session, challenge_token: str) -> User:
    payload = decode_token(challenge_token)
    if not payload or payload.get("type") != "login_2fa":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired challenge")
    try:
        user = db.get(User, int(payload["sub"]))
    except (KeyError, ValueError, TypeError):
        user = None
    if user is None or not user.is_active or not user.is_2fa_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired challenge")
    return user


@router.post("/login/verify", response_model=LoginVerifyResponse)
def login_verify(
    body: LoginVerifyRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> LoginVerifyResponse:
    user = _challenge_user(db, body.challenge_token)
    if not otp.verify_code(user, body.code, "login"):
        db.commit()  # persist the attempt increment
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code")

    _record_login(db, user, request)
    trust_token: str | None = None
    if body.trust_device:
        label = request.headers.get("user-agent", "")[:255]
        trust_token = trusted_devices.trust_device(db, user, label)
        response.set_cookie(
            key=settings.trusted_device_cookie_name,
            value=trust_token,
            max_age=settings.trusted_device_ttl_days * 24 * 3600,
            httponly=True, secure=True, samesite="lax",
        )
    access, refresh = _issue_token_pair(user)
    return LoginVerifyResponse(
        access_token=access, refresh_token=refresh,
        force_password_change=user.force_password_change or user.is_password_expired,
        trust_token=trust_token,
    )


@router.post("/login/resend", response_model=Message)
def login_resend(body: ResendRequest, db: Session = Depends(get_db)) -> Message:
    user = _challenge_user(db, body.challenge_token)
    if user.otp_purpose != "login":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active login challenge")
    code = otp.resend_code(user)
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another code",
        )
    db.commit()
    send_2fa_code(user.email, code)
    return Message(detail="A new code has been sent")
```

In `backend/tests/test_auth.py`, delete `test_2fa_required_and_verified` (lines ~173-196) and its now-unused imports (`pyotp`, `encrypt_secret`) — the email-flow equivalents live in `test_2fa_login.py`. (Leave `UserRole` if still used elsewhere in the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_2fa_login.py tests/test_auth.py -v`
Expected: PASS (new 2FA login tests + all remaining auth tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/v1/auth.py backend/tests/test_2fa_login.py backend/tests/test_auth.py
git commit -m "feat: email-OTP login (challenge/verify/resend) + trusted-device pre-check"
```

---

### Task 9: Profile — email 2FA enroll / verify / dismiss / disable / status

**Files:**
- Modify: `backend/app/schemas/profile.py`
- Modify: `backend/app/api/v1/profile.py` (replace the TOTP setup/verify/disable/status endpoints with the email flow)
- Modify: `backend/tests/test_profile.py` (replace the TOTP lifecycle tests)

**Interfaces:**
- Consumes: `otp.*`, `email.send_2fa_code`, `trusted_devices.revoke_all`.
- Produces endpoints (all `Depends(get_current_user)`):
  - `GET /profile/2fa/status` → `TwoFAStatus{enabled, method, enrollment_prompted}`
  - `POST /profile/2fa/enroll` `{method: 'email'}` → `Message` (emails a test code; does not activate)
  - `POST /profile/2fa/enroll/verify` `{code}` → `Message` (activates: `two_factor_enabled=True`, `method='email'`, `enrollment_prompted=True`)
  - `POST /profile/2fa/enrollment-dismiss` → `Message` (`enrollment_prompted=True`)
  - `POST /profile/2fa/disable` → `Message` (clears 2FA + pending code + revokes trusted devices)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_profile.py  (replace the TOTP 2FA tests; keep the profile CRUD tests)
from collections.abc import Callable

import app.services.email as email
import app.services.otp as otp
from app.models import User
from fastapi.testclient import TestClient


def _fixed(monkeypatch, code="123456"):
    monkeypatch.setattr(otp, "generate_code", lambda: code)
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)


def test_2fa_status_starts_disabled(client: TestClient, auth_headers) -> None:
    body = client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()
    assert body["enabled"] is False
    assert body["method"] is None


def test_email_enroll_lifecycle(client: TestClient, auth_headers, monkeypatch) -> None:
    _fixed(monkeypatch)
    # Enroll sends a test code but does not activate.
    assert client.post(
        "/api/v1/profile/2fa/enroll", headers=auth_headers, json={"method": "email"}
    ).status_code == 200
    assert client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()["enabled"] is False
    # Verifying the code activates it.
    ok = client.post("/api/v1/profile/2fa/enroll/verify", headers=auth_headers, json={"code": "123456"})
    assert ok.status_code == 200
    status_body = client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()
    assert status_body["enabled"] is True and status_body["method"] == "email"
    # Disable turns it off.
    assert client.post("/api/v1/profile/2fa/disable", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()["enabled"] is False


def test_enroll_verify_wrong_code_is_400(client: TestClient, auth_headers, monkeypatch) -> None:
    _fixed(monkeypatch)
    client.post("/api/v1/profile/2fa/enroll", headers=auth_headers, json={"method": "email"})
    resp = client.post("/api/v1/profile/2fa/enroll/verify", headers=auth_headers, json={"code": "000000"})
    assert resp.status_code == 400


def test_enrollment_dismiss_sets_flag(client: TestClient, auth_headers) -> None:
    assert client.post("/api/v1/profile/2fa/enrollment-dismiss", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()["enrollment_prompted"] is True


def test_enroll_rejects_unknown_method(client: TestClient, auth_headers) -> None:
    resp = client.post("/api/v1/profile/2fa/enroll", headers=auth_headers, json={"method": "sms"})
    assert resp.status_code == 400
```

Delete the old `test_2fa_full_lifecycle`, `test_2fa_verify_before_setup_is_400`, `test_2fa_verify_wrong_code_is_400`, and `test_2fa_setup_blocked_when_not_allowed`, plus the `pyotp` import. Keep `test_profile_requires_auth` and `test_get_and_update_profile`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_profile.py -v`
Expected: FAIL (`/profile/2fa/status` 404, etc.).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas/profile.py`, replace the TOTP schemas with:

```python
class TwoFAStatus(ORMModel):
    """2FA enablement status for the current user."""
    enabled: bool
    method: str | None = None
    enrollment_prompted: bool = False


class TwoFAEnrollRequest(BaseModel):
    method: str = "email"


class TwoFAVerifyRequest(BaseModel):
    code: str
```

Rewrite `backend/app/api/v1/profile.py` — drop `import pyotp` and the Fernet/TOTP setup logic; replace the four `/2fa*` endpoints with:

```python
from app.services import otp, trusted_devices
from app.services.email import send_2fa_code
from app.schemas.profile import (
    ProfileUpdate, TwoFAEnrollRequest, TwoFAStatus, TwoFAVerifyRequest,
)
from app.schemas.common import Message


@router.get("/2fa/status", response_model=TwoFAStatus)
def get_2fa_status(user: User = Depends(get_current_user)) -> TwoFAStatus:
    return TwoFAStatus(
        enabled=user.is_2fa_active,
        method=user.two_factor_method,
        enrollment_prompted=user.two_factor_enrollment_prompted,
    )


@router.post("/2fa/enroll", response_model=Message)
def enroll_2fa(
    body: TwoFAEnrollRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    if not user.can_enable_2fa:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="2FA not allowed for this account")
    if body.method != "email":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported 2FA method")
    code = otp.issue_code(user, "enroll")
    db.commit()
    send_2fa_code(user.email, code)
    return Message(detail="A verification code has been sent to your email")


@router.post("/2fa/enroll/verify", response_model=Message)
def verify_enroll_2fa(
    body: TwoFAVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    if not otp.verify_code(user, body.code, "enroll"):
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")
    user.two_factor_enabled = True
    user.two_factor_method = "email"
    user.two_factor_enrollment_prompted = True
    db.commit()
    return Message(detail="Two-factor authentication enabled")


@router.post("/2fa/enrollment-dismiss", response_model=Message)
def dismiss_enrollment(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    user.two_factor_enrollment_prompted = True
    db.commit()
    return Message(detail="Enrollment prompt dismissed")


@router.post("/2fa/disable", response_model=Message)
def disable_2fa(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    user.two_factor_enabled = False
    user.two_factor_method = None
    otp.clear_code(user)
    trusted_devices.revoke_all(db, user)
    db.commit()
    return Message(detail="Two-factor authentication disabled")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_profile.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/profile.py backend/app/api/v1/profile.py backend/tests/test_profile.py
git commit -m "feat: email 2FA enroll/verify/dismiss/disable on profile"
```

---

### Task 10: Profile — trusted-device management

**Files:**
- Modify: `backend/app/schemas/profile.py` (add `TrustedDeviceOut`)
- Modify: `backend/app/api/v1/profile.py` (list / revoke / revoke-others)
- Test: `backend/tests/test_trusted_devices_api.py` (create)

**Interfaces:**
- Consumes: `trusted_devices.list_devices/revoke/revoke_all`, `settings.trusted_device_cookie_name`.
- Produces:
  - `GET /profile/trusted-devices` → `list[TrustedDeviceOut]`
  - `DELETE /profile/trusted-devices/{device_id}` → `Message`
  - `POST /profile/trusted-devices/revoke-others` → `Message`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_trusted_devices_api.py
import app.services.email as email
import app.services.otp as otp
from fastapi.testclient import TestClient


def _fixed(monkeypatch, code="123456"):
    monkeypatch.setattr(otp, "generate_code", lambda: code)
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)


def _login_2fa_with_trust(client, username, password):
    challenge = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    ).json()["challenge_token"]
    return client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": True},
    ).json()


def test_list_and_revoke_trusted_devices(client: TestClient, make_user, monkeypatch) -> None:
    _fixed(monkeypatch)
    make_user("dv", "Recruit123!", two_factor_enabled=True, two_factor_method="email")
    tokens = _login_2fa_with_trust(client, "dv", "Recruit123!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    devices = client.get("/api/v1/profile/trusted-devices", headers=headers).json()
    assert len(devices) == 1
    device_id = devices[0]["id"]

    assert client.delete(f"/api/v1/profile/trusted-devices/{device_id}", headers=headers).status_code == 200
    assert client.get("/api/v1/profile/trusted-devices", headers=headers).json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_trusted_devices_api.py -v`
Expected: FAIL (`/profile/trusted-devices` 404).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas/profile.py` add:

```python
from datetime import datetime


class TrustedDeviceOut(ORMModel):
    id: int
    device_label: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
```

In `backend/app/api/v1/profile.py` add (import `Request`, `settings`, `TrustedDeviceOut`):

```python
@router.get("/trusted-devices", response_model=list[TrustedDeviceOut])
def list_trusted_devices(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    return trusted_devices.list_devices(db, user)


@router.delete("/trusted-devices/{device_id}", response_model=Message)
def revoke_trusted_device(
    device_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    if not trusted_devices.revoke(db, user, device_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return Message(detail="Device revoked")


@router.post("/trusted-devices/revoke-others", response_model=Message)
def revoke_other_trusted_devices(
    request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    current = request.cookies.get(settings.trusted_device_cookie_name)
    n = trusted_devices.revoke_all(db, user, except_token=current)
    return Message(detail=f"Revoked {n} device(s)")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_trusted_devices_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/profile.py backend/app/api/v1/profile.py backend/tests/test_trusted_devices_api.py
git commit -m "feat: trusted-device management endpoints on profile"
```

---

### Task 11: Admin — enable/disable 2FA + revoke trusted devices

**Files:**
- Modify: `backend/app/schemas/admin.py` (`AdminUserUpdate` gains `two_factor_enabled`)
- Modify: `backend/app/api/v1/admin.py` (handle the toggle in `update_user`; add revoke endpoint)
- Test: `backend/tests/test_admin_2fa.py` (create)

**Interfaces:**
- Consumes: `trusted_devices.revoke_all`, `otp.clear_code`.
- Produces:
  - `AdminUserUpdate.two_factor_enabled: bool | None = None`
  - `update_user`: `True` → `two_factor_enabled=True, method='email'`; `False` → disable + clear code + revoke devices
  - `POST /admin/users/{user_id}/revoke-trusted-devices` → `Message`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_admin_2fa.py
from collections.abc import Callable

import app.services.email as email
import app.services.otp as otp
from app.models import User
from fastapi.testclient import TestClient


def test_admin_enable_forces_2fa_next_login(
    client: TestClient, auth_headers, make_user: Callable[..., User], login, monkeypatch
) -> None:
    monkeypatch.setattr(otp, "generate_code", lambda: "123456")
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)
    target = make_user("victim", "Recruit123!")

    resp = client.patch(
        f"/api/v1/admin/users/{target.id}",
        headers=auth_headers,
        json={"two_factor_enabled": True},
    )
    assert resp.status_code == 200
    assert resp.json()["two_factor_enabled"] is True
    assert resp.json()["two_factor_method"] == "email"

    # Next login now demands a code.
    body = login(client, "victim", "Recruit123!").json()
    assert body["two_factor_required"] is True


def test_admin_disable_clears_2fa(
    client: TestClient, auth_headers, make_user: Callable[..., User]
) -> None:
    target = make_user("hasit", two_factor_enabled=True, two_factor_method="email")
    resp = client.patch(
        f"/api/v1/admin/users/{target.id}",
        headers=auth_headers,
        json={"two_factor_enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["two_factor_enabled"] is False
    assert resp.json()["two_factor_method"] is None


def test_admin_revoke_trusted_devices(
    client: TestClient, auth_headers, make_user: Callable[..., User]
) -> None:
    target = make_user("trusted", two_factor_enabled=True, two_factor_method="email")
    resp = client.post(
        f"/api/v1/admin/users/{target.id}/revoke-trusted-devices", headers=auth_headers
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_admin_2fa.py -v`
Expected: FAIL (unknown field `two_factor_enabled` ignored / revoke endpoint 404).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas/admin.py`, add to `AdminUserUpdate`:

```python
    two_factor_enabled: bool | None = None
```

In `backend/app/api/v1/admin.py` — import the services and handle the toggle inside `update_user` *before* `crud.update` (so it isn't blindly `setattr`):

```python
from app.services import otp, trusted_devices
```

Inside `update_user`, right after computing `data = body.model_dump(exclude_unset=True)` and `changed_fields`:

```python
    # 2FA is a derived toggle, not a raw column write.
    if "two_factor_enabled" in data:
        enable = data.pop("two_factor_enabled")
        if enable:
            user.two_factor_enabled = True
            user.two_factor_method = "email"
        else:
            user.two_factor_enabled = False
            user.two_factor_method = None
            otp.clear_code(user)
            trusted_devices.revoke_all(db, user)
```

(`crud.update(db, user, data)` then persists the rest and commits `user` in the same session.)

Add the revoke endpoint after `update_user`:

```python
@router.post("/users/{user_id}/revoke-trusted-devices", response_model=Message)
def admin_revoke_trusted_devices(
    user_id: int,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Message:
    user = _get_or_404(db, user_id)
    n = trusted_devices.revoke_all(db, user)
    record_activity(
        db, user=actor, action="UPDATE", table_name="users",
        record_id=user.id, record_description=user.username,
        details="revoked trusted devices", request=request,
    )
    return Message(detail=f"Revoked {n} device(s)")
```

Add `from app.schemas.common import Message` to the imports if not already present (`Page` is imported from `common`; add `Message`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_admin_2fa.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/api/v1/admin.py backend/tests/test_admin_2fa.py
git commit -m "feat: admin enable/disable 2FA + revoke trusted devices"
```

---

### Task 12: Auto-revoke trusted devices on password change/reset

**Files:**
- Modify: `backend/app/api/v1/auth.py` (`change_password`, `reset_password`)
- Test: `backend/tests/test_2fa_password_revoke.py` (create)

**Interfaces:**
- Consumes: `trusted_devices.revoke_all`.
- Produces: both password-change paths revoke the user's trusted devices.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_2fa_password_revoke.py
from collections.abc import Callable

import app.services.email as email
import app.services.otp as otp
from app.models import TrustedDevice, User
from fastapi.testclient import TestClient
from tests.conftest import TestingSessionLocal


def _count_live_devices(user_id: int) -> int:
    with TestingSessionLocal() as db:
        return (
            db.query(TrustedDevice)
            .filter(TrustedDevice.user_id == user_id, TrustedDevice.revoked_at.is_(None))
            .count()
        )


def test_change_password_revokes_trusted_devices(
    client: TestClient, make_user: Callable[..., User], monkeypatch
) -> None:
    monkeypatch.setattr(otp, "generate_code", lambda: "123456")
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)
    user = make_user("pw", "OldPass123!", two_factor_enabled=True, two_factor_method="email")
    challenge = client.post(
        "/api/v1/auth/login", json={"username": "pw", "password": "OldPass123!"}
    ).json()["challenge_token"]
    tokens = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": True},
    ).json()
    assert _count_live_devices(user.id) == 1

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "OldPass123!", "new_password": "BrandNew123!"},
    )
    assert resp.status_code == 200
    assert _count_live_devices(user.id) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_2fa_password_revoke.py -v`
Expected: FAIL (device still live after password change).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/api/v1/auth.py`, in `change_password` after `_apply_new_password(db, user, body.new_password)` and before `db.commit()`:

```python
    trusted_devices.revoke_all(db, user)
```

In `reset_password`, after `_apply_new_password(db, user, body.new_password)` (before the final `db.commit()`):

```python
    trusted_devices.revoke_all(db, user)
```

(`revoke_all` commits internally; the subsequent `db.commit()` is harmless.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_2fa_password_revoke.py tests/test_auth.py -v`
Expected: PASS (new test + existing password tests still green).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/auth.py backend/tests/test_2fa_password_revoke.py
git commit -m "feat: revoke trusted devices on password change/reset"
```

---

### Task 13: Expose 2FA enrollment state on `UserOut`

**Files:**
- Modify: `backend/app/schemas/auth.py` (`UserOut`)
- Test: `backend/tests/test_userout_2fa_fields.py` (create)

**Interfaces:**
- Produces: `UserOut` gains `two_factor_enabled: bool`, `two_factor_method: str | None`, `two_factor_enrollment_prompted: bool` — clients read these from `/auth/me` to decide whether to show the one-time enrollment prompt.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_userout_2fa_fields.py
from fastapi.testclient import TestClient


def test_me_exposes_2fa_enrollment_fields(client: TestClient, auth_headers) -> None:
    body = client.get("/api/v1/auth/me", headers=auth_headers).json()
    assert body["two_factor_enabled"] is False
    assert body["two_factor_method"] is None
    assert body["two_factor_enrollment_prompted"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_userout_2fa_fields.py -v`
Expected: FAIL (`KeyError: 'two_factor_enabled'`).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas/auth.py`, add to `UserOut` (after `is_2fa_active`):

```python
    two_factor_enabled: bool = False
    two_factor_method: str | None = None
    two_factor_enrollment_prompted: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_userout_2fa_fields.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/tests/test_userout_2fa_fields.py
git commit -m "feat: expose 2FA enrollment state on UserOut"
```

---

## Final verification

- [ ] Run the full suite: `cd backend && uv run pytest -q` — expected: all green (existing + new).
- [ ] Sanity-check the OpenAPI shape drift for the clients: `cd backend && uv run python -c "from app.main import app; import json; print(len(app.openapi()['paths']))"` (the new `/auth/login/verify`, `/auth/login/resend`, `/profile/2fa/*`, `/profile/trusted-devices/*`, and `/admin/users/{id}/revoke-trusted-devices` paths should be present).
- [ ] Regenerate `shared/openapi.json` / `web/src/api/schema.d.ts` per the repo's existing generation step (this feeds the Web plan).

## Spec coverage check

- Email OTP mechanism → Tasks 5, 7, 8, 9. Method-based scaffold (`email`/`totp` dormant) → Tasks 2, 8. First-login *ask-once* enrollment (verify test code first) → Tasks 9, 13. Admin immediate-enforce toggle → Task 11. Dedicated verify step (challenge token) → Task 8. Trusted devices (30-day, full management, auto-revoke) → Tasks 3, 6, 8, 10, 11, 12. Code policy → Tasks 1, 5. Migration → Task 4.
- **Deferred to their own plans:** Web client and iOS client (this plan is backend-only; the API is the contract they build against).
