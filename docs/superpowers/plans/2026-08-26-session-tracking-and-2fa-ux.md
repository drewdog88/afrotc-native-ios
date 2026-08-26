# Session Tracking + 2FA UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a server-side session store so a signed-in user can see and remotely sign out the devices logged into their account, and fix three 2FA UX problems (blocking enrollment popup, missing on/off toggle, off-theme code box).

**Architecture:** Each login mints a `sid` (session id) embedded in the access + refresh JWTs and backed by an `auth_sessions` row. `get_current_user` validates the session on every request, so revoking a session logs that device out immediately. Web gets a "Signed-in devices" card, a real 2FA toggle, and a non-blocking enrollment banner.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (typed `Mapped`) + Alembic + Neon Postgres; React 19 + Vite + @tanstack/react-query + react-router; pytest (SQLite in-memory harness) + vitest.

**Spec:** `docs/superpowers/specs/2026-08-26-session-tracking-and-2fa-ux-design.md`

## Global Constraints

- **Timezone in services/models:** call `security.now_utc()` via the module (never `from ... import now_utc`) so the test harness's tz-naive patch applies. Follow `app/services/trusted_devices.py`.
- **Additive migration only:** new table `auth_sessions`; `down_revision = "email2fa0001"` (verified current head). Safe to apply to the **direct** (non-`-pooler`) Neon host before deploy.
- **`sid`-less tokens are invalid:** access/refresh tokens issued before this change carry no `sid` and are rejected → everyone re-logs in once after deploy. Acceptable (2 users). This also means **existing tests that mint tokens directly must be updated** (see Task 9).
- **Never leak `sid` to the client** — the sessions API returns a `current: bool`, never the raw `sid`.
- **Trusted devices are unchanged** — a separate concept; keep the existing card and endpoints.
- **iOS app scope:** backend changes apply to it (one-time re-login only); the sessions-management UI is web-only this pass. Do not modify iOS Swift.
- Commit after each task. Do **not** push or merge — integration happens via the finishing skill at the end.

## File Structure

**Backend (create):**
- `backend/app/models/auth_session.py` — `AuthSession` ORM model.
- `backend/app/services/sessions.py` — session lifecycle (start/list/revoke/revoke_others + device label).
- `backend/alembic/versions/2026_08_26_auth_sessions.py` — additive migration.
- `backend/tests/test_auth_session_model.py`, `test_sessions_service.py`, `test_sessions_api.py`, `test_sessions_auth.py` — new tests.

**Backend (modify):**
- `backend/app/models/__init__.py` — export `AuthSession`.
- `backend/app/core/security.py` — `create_refresh_token` gains `extra`.
- `backend/app/api/deps.py` — `get_current_session` + refactor `get_current_user`.
- `backend/app/api/v1/auth.py` — create a session on every login path; refresh validates + bumps; logout revokes.
- `backend/app/api/v1/profile.py` — `GET/DELETE /profile/sessions*`.
- `backend/app/api/v1/admin.py` — `POST /admin/users/{id}/revoke-sessions`.
- `backend/app/schemas/profile.py` — `SessionOut`.
- Existing tests touching logout/token-minting (Task 9).

**Web (create):**
- `web/src/components/EnrollmentBanner.tsx` — non-blocking replacement for `EnrollmentPrompt`.
- `web/src/lib/api.sessions.test.ts` — client test.

**Web (modify):**
- `web/src/lib/api.ts` — `listSessions`/`revokeSession`/`revokeOtherSessions` + local `SessionOut` type.
- `web/src/pages/Profile.tsx` — `SignedInDevicesCard` + toggle-based `TwoFactorCard`.
- `web/src/pages/Profile.module.css` — switch + session-row styles.
- `web/src/components/AppShell.tsx` — render `EnrollmentBanner`.
- `web/src/pages/LoginVerify.tsx` + `web/src/index.css` — themed `.otp-input`.
- **Delete** `web/src/components/EnrollmentPrompt.tsx`.

**Ops/docs (modify):** `.github/workflows/restore-drill.yml`, `wiki/Backups-and-Recovery.md`, `wiki/Database.md`, `wiki/Testing.md`, `README.md`, `backend/README.md`.

---

### Task 1: `AuthSession` model + migration

**Files:**
- Create: `backend/app/models/auth_session.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/2026_08_26_auth_sessions.py`
- Test: `backend/tests/test_auth_session_model.py`

**Interfaces:**
- Produces: `AuthSession(id, user_id, sid, device_label, ip_address, user_agent, created_at, last_seen_at, expires_at, revoked_at)`; importable as `from app.models import AuthSession`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_auth_session_model.py`

```python
from datetime import timedelta

from app.core import security
from app.models import AuthSession, User
from app.core.security import hash_password
from app.models.enums import UserRole
from tests.conftest import TestingSessionLocal


def _user(db) -> User:
    u = User(
        username="sess", email="sess@det695.local", password_hash=hash_password("x"),
        first_name="S", last_name="S", role=UserRole.RECRUITER.value, is_active=True,
        password_expires_at=None, secret_question="q", secret_answer_hash=hash_password("a"),
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_auth_session_roundtrips():
    with TestingSessionLocal() as db:
        user = _user(db)
        now = security.now_utc()
        row = AuthSession(
            user_id=user.id, sid="abc123", device_label="Chrome on macOS",
            ip_address="1.2.3.4", user_agent="UA", created_at=now,
            last_seen_at=now, expires_at=now + timedelta(days=14),
        )
        db.add(row); db.commit(); db.refresh(row)
        assert row.id is not None
        assert row.revoked_at is None
        assert row.sid == "abc123"
```

- [ ] **Step 2: Run it, verify it fails** — `cd backend && uv run pytest tests/test_auth_session_model.py -q` → FAIL (`ImportError: cannot import name 'AuthSession'`).

- [ ] **Step 3: Create the model** — `backend/app/models/auth_session.py` (mirror `trusted_device.py`)

```python
"""Auth sessions — one row per login; the sid claim in a token points here."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    sid: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    device_label: Mapped[str] = mapped_column(String(255), default="")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Register it** — in `backend/app/models/__init__.py` add `from app.models.auth_session import AuthSession` and add `"AuthSession",` to `__all__` (keep alphabetical: first entry).

- [ ] **Step 5: Run the test, verify it passes** — `uv run pytest tests/test_auth_session_model.py -q` → PASS.

- [ ] **Step 6: Write the migration** — `backend/alembic/versions/2026_08_26_auth_sessions.py`

```python
"""auth sessions

Additive: a new auth_sessions table backing the sid claim in access/refresh tokens.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "authsess0001"
down_revision = "email2fa0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("sid", sa.String(length=36), nullable=False),
        sa.Column("device_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_sessions_sid", "auth_sessions", ["sid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_sid", table_name="auth_sessions")
    op.drop_table("auth_sessions")
```

- [ ] **Step 7: Verify migration chains** — `uv run alembic heads` shows a single head `authsess0001`. (Do not run `upgrade` against a real DB here.)

- [ ] **Step 8: Commit** — `git add -A && git commit -m "feat(sessions): AuthSession model + migration"`

---

### Task 2: sessions service

**Files:**
- Create: `backend/app/services/sessions.py`
- Test: `backend/tests/test_sessions_service.py`

**Interfaces:**
- Consumes: `AuthSession` (Task 1); `security.now_utc`, `settings.refresh_token_expire_days`.
- Produces:
  - `start(db, user, request) -> AuthSession`
  - `list_active(db, user) -> list[AuthSession]`
  - `revoke(db, user, session_id) -> bool`
  - `revoke_others(db, user, except_sid) -> int`
  - `revoke_all(db, user) -> int`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_sessions_service.py`

```python
from types import SimpleNamespace

from app.core import security
from app.core.security import hash_password
from app.models import AuthSession, User
from app.models.enums import UserRole
from app.services import sessions
from tests.conftest import TestingSessionLocal


def _user(db, name="u"):
    u = User(username=name, email=f"{name}@det695.local", password_hash=hash_password("x"),
             first_name="A", last_name="B", role=UserRole.RECRUITER.value, is_active=True,
             password_expires_at=None, secret_question="q", secret_answer_hash=hash_password("a"))
    db.add(u); db.commit(); db.refresh(u)
    return u


def _req(ua="Mozilla/5.0 (Macintosh) Chrome/120", ip="9.9.9.9"):
    return SimpleNamespace(headers={"user-agent": ua, "x-forwarded-for": ip},
                           client=SimpleNamespace(host="127.0.0.1"), cookies={})


def test_start_creates_active_session():
    with TestingSessionLocal() as db:
        user = _user(db)
        s = sessions.start(db, user, _req())
        assert s.sid and len(s.sid) <= 36
        assert s.revoked_at is None
        assert s.expires_at > security.now_utc()
        assert s.ip_address == "9.9.9.9"
        assert s.device_label  # non-empty label derived from UA


def test_list_active_excludes_revoked_and_orders_recent_first():
    with TestingSessionLocal() as db:
        user = _user(db)
        a = sessions.start(db, user, _req())
        b = sessions.start(db, user, _req())
        assert sessions.revoke(db, user, a.id) is True
        active = sessions.list_active(db, user)
        assert [s.id for s in active] == [b.id]


def test_revoke_scoped_to_user():
    with TestingSessionLocal() as db:
        u1, u2 = _user(db, "one"), _user(db, "two")
        s = sessions.start(db, u1, _req())
        assert sessions.revoke(db, u2, s.id) is False  # not u2's
        assert sessions.revoke(db, u1, s.id) is True


def test_revoke_others_keeps_current():
    with TestingSessionLocal() as db:
        user = _user(db)
        keep = sessions.start(db, user, _req())
        sessions.start(db, user, _req())
        sessions.start(db, user, _req())
        n = sessions.revoke_others(db, user, keep.sid)
        assert n == 2
        assert [s.id for s in sessions.list_active(db, user)] == [keep.id]
```

- [ ] **Step 2: Run it, verify it fails** — `uv run pytest tests/test_sessions_service.py -q` → FAIL (`ModuleNotFoundError: app.services.sessions`).

- [ ] **Step 3: Implement the service** — `backend/app/services/sessions.py`

```python
"""Auth-session lifecycle: one row per login, revocable for remote sign-out."""
from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models import User
from app.models.auth_session import AuthSession
from app.services.activity import _client_ip


def _device_label(user_agent: str | None) -> str:
    """A short human label from the UA string; best-effort, never raises."""
    ua = user_agent or ""
    browser = next((b for b in ("Edg", "Chrome", "Firefox", "Safari") if b in ua), None)
    browser = {"Edg": "Edge"}.get(browser, browser)
    os_name = next((o for o, key in (("macOS", "Macintosh"), ("Windows", "Windows"),
                                     ("iPhone", "iPhone"), ("iPad", "iPad"),
                                     ("Android", "Android"), ("Linux", "Linux"))
                    if key in ua), None)
    if browser and os_name:
        return f"{browser} on {os_name}"
    if browser or os_name:
        return browser or os_name
    return (ua[:255] or "Unknown device")


def start(db: Session, user: User, request: Request) -> AuthSession:
    now = security.now_utc()
    ua = request.headers.get("user-agent") if request is not None else None
    row = AuthSession(
        user_id=user.id,
        sid=uuid.uuid4().hex,
        device_label=_device_label(ua)[:255],
        ip_address=_client_ip(request),
        user_agent=(ua[:500] if ua else None),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_valid(db: Session, sid: str | None) -> AuthSession | None:
    if not sid:
        return None
    row = db.scalar(select(AuthSession).where(AuthSession.sid == sid))
    if row is None or row.revoked_at is not None or row.expires_at <= security.now_utc():
        return None
    return row


def touch(db: Session, session: AuthSession) -> None:
    session.last_seen_at = security.now_utc()
    db.commit()


def list_active(db: Session, user: User) -> list[AuthSession]:
    now = security.now_utc()
    return list(db.scalars(
        select(AuthSession)
        .where(AuthSession.user_id == user.id,
               AuthSession.revoked_at.is_(None),
               AuthSession.expires_at > now)
        .order_by(AuthSession.last_seen_at.desc())
    ))


def revoke(db: Session, user: User, session_id: int) -> bool:
    row = db.get(AuthSession, session_id)
    if row is None or row.user_id != user.id or row.revoked_at is not None:
        return False
    row.revoked_at = security.now_utc()
    db.commit()
    return True


def revoke_others(db: Session, user: User, except_sid: str | None) -> int:
    rows = db.scalars(select(AuthSession).where(
        AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))).all()
    now = security.now_utc()
    n = 0
    for row in rows:
        if except_sid and row.sid == except_sid:
            continue
        row.revoked_at = now
        n += 1
    db.commit()
    return n


def revoke_all(db: Session, user: User) -> int:
    return revoke_others(db, user, except_sid=None)
```

- [ ] **Step 4: Run the tests, verify they pass** — `uv run pytest tests/test_sessions_service.py -q` → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat(sessions): session lifecycle service"`

---

### Task 3: `sid` in tokens + `get_current_session` dependency

**Files:**
- Modify: `backend/app/core/security.py:65-66` (`create_refresh_token`)
- Modify: `backend/app/api/deps.py`
- Test: extend `backend/tests/test_sessions_auth.py` (create)

**Interfaces:**
- Consumes: `sessions.get_valid` (Task 2).
- Produces: `create_refresh_token(subject, extra=None)`; `get_current_session(creds, db) -> AuthSession`; `get_current_user` now derives the user from the validated session's `user_id`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_sessions_auth.py`

```python
from datetime import timedelta

from app.core import security
from app.core.security import create_access_token, hash_password
from app.models import AuthSession, User
from app.models.enums import UserRole
from tests.conftest import TestingSessionLocal


def _seed_user_and_session(sid="s-live"):
    with TestingSessionLocal() as db:
        u = User(username="live", email="live@det695.local", password_hash=hash_password("x"),
                 first_name="L", last_name="V", role=UserRole.RECRUITER.value, is_active=True,
                 password_expires_at=None, secret_question="q", secret_answer_hash=hash_password("a"))
        db.add(u); db.commit(); db.refresh(u)
        now = security.now_utc()
        db.add(AuthSession(user_id=u.id, sid=sid, device_label="d", created_at=now,
                           last_seen_at=now, expires_at=now + timedelta(days=1)))
        db.commit()
        return u.id


def test_access_token_without_sid_is_rejected(client):
    _seed_user_and_session()
    token = create_access_token("1")  # no sid claim
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_access_token_with_valid_session_passes(client):
    uid = _seed_user_and_session(sid="s-ok")
    token = create_access_token(str(uid), {"sid": "s-ok"})
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_access_token_with_revoked_session_is_rejected(client):
    uid = _seed_user_and_session(sid="s-rev")
    token = create_access_token(str(uid), {"sid": "s-rev"})
    with TestingSessionLocal() as db:
        row = db.query(AuthSession).filter_by(sid="s-rev").one()
        row.revoked_at = security.now_utc(); db.commit()
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run it, verify it fails** — `uv run pytest tests/test_sessions_auth.py -q` → the `with_valid_session` case FAILS (current `get_current_user` ignores sessions, so a sid-less token would even pass). Confirms behavior change is needed.

- [ ] **Step 3: Add `extra` to `create_refresh_token`** — `backend/app/core/security.py`

```python
def create_refresh_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject, "refresh", timedelta(days=settings.refresh_token_expire_days), extra
    )
```

- [ ] **Step 4: Rewrite deps** — `backend/app/api/deps.py` (replace the `get_current_user` block)

```python
from app.core import security
from app.core.security import decode_token
from app.models import AuthSession, User
from app.services import sessions


def get_current_session(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthSession:
    if creds is None:
        raise _UNAUTHORIZED
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise _UNAUTHORIZED
    session = sessions.get_valid(db, payload.get("sid"))
    if session is None:
        raise _UNAUTHORIZED
    return session


def get_current_user(
    session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    return user
```

(Keep `require_admin` / `require_write` / `pagination` as-is; they depend on `get_current_user`.)

- [ ] **Step 5: Run the new test file, verify it passes** — `uv run pytest tests/test_sessions_auth.py -q` → PASS (revoked/sid-less rejected, valid passes).

- [ ] **Step 6: Commit** — `git commit -am "feat(sessions): validate session on every request via sid"`

---

### Task 4: wire sessions into login / refresh / logout

**Files:**
- Modify: `backend/app/api/v1/auth.py` (`_issue_token_pair`, `login`, `login_verify`, `refresh`, `logout`)
- Test: `backend/tests/test_sessions_auth.py` (extend)

**Interfaces:**
- Consumes: `sessions.start/get_valid/touch/revoke` (Task 2), `get_current_session` (Task 3).
- Produces: every successful login creates one `AuthSession`; `/auth/logout` revokes the caller's; `/auth/refresh` requires a live session and bumps `last_seen_at`.

- [ ] **Step 1: Write failing tests** — append to `backend/tests/test_sessions_auth.py`

```python
def test_login_creates_session_and_logout_revokes(client, make_user):
    make_user("recruiter1", "Recruit123!")
    r = client.post("/api/v1/auth/login", json={"username": "recruiter1", "password": "Recruit123!"})
    assert r.status_code == 200
    access = r.json()["access_token"]
    h = {"Authorization": f"Bearer {access}"}
    assert client.get("/api/v1/auth/me", headers=h).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=h).status_code == 204
    # session revoked → the same access token no longer works
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_refresh_fails_after_logout(client, make_user):
    make_user("recruiter2", "Recruit123!")
    r = client.post("/api/v1/auth/login", json={"username": "recruiter2", "password": "Recruit123!"})
    refresh = r.json()["refresh_token"]
    access = r.json()["access_token"]
    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access}"})
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401
```

- [ ] **Step 2: Run, verify it fails** — `uv run pytest tests/test_sessions_auth.py -q` → the logout/refresh cases FAIL (logout is a no-op today).

- [ ] **Step 3: Edit `auth.py`.** Add imports: `from app.api.deps import get_current_session` and `from app.models import AuthSession` and `from app.services import otp, trusted_devices, sessions`. Then:

Replace `_issue_token_pair`:
```python
def _issue_token_pair(user: User, sid: str) -> tuple[str, str]:
    subject = str(user.id)
    claim = {"sid": sid}
    return create_access_token(subject, claim), create_refresh_token(subject, claim)
```

In `login` — the trusted-device fast path and the no-2FA path both currently call `_issue_token_pair(user)`. Change each to start a session first:
```python
        if trusted_devices.find_valid(db, user, body.trust_token or cookie_token):
            _record_login(db, user, request)
            session = sessions.start(db, user, request)
            access, refresh = _issue_token_pair(user, session.sid)
            return LoginResponse(access_token=access, refresh_token=refresh,
                force_password_change=user.force_password_change or user.is_password_expired)
```
and the final no-2FA path:
```python
    _record_login(db, user, request)
    session = sessions.start(db, user, request)
    access, refresh = _issue_token_pair(user, session.sid)
    return LoginResponse(access_token=access, refresh_token=refresh,
        force_password_change=user.force_password_change or user.is_password_expired)
```

In `login_verify`, after `_record_login(...)` and the trust-device block, replace the issue line:
```python
    session = sessions.start(db, user, request)
    access, refresh = _issue_token_pair(user, session.sid)
    return LoginVerifyResponse(access_token=access, refresh_token=refresh,
        force_password_change=user.force_password_change or user.is_password_expired,
        trust_token=trust_token)
```

Replace `refresh`:
```python
@router.post("/refresh", response_model=AccessToken)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> AccessToken:
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    session = sessions.get_valid(db, payload.get("sid"))
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    sessions.touch(db, session)
    return AccessToken(access_token=create_access_token(str(user.id), {"sid": session.sid}))
```

Replace `logout`:
```python
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> None:
    session.revoked_at = now_utc()
    db.commit()
    return None
```

- [ ] **Step 4: Run the file, verify it passes** — `uv run pytest tests/test_sessions_auth.py -q` → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat(sessions): create on login, revoke on logout, validate on refresh"`

---

### Task 5: `/profile/sessions` endpoints

**Files:**
- Modify: `backend/app/schemas/profile.py` (add `SessionOut`)
- Modify: `backend/app/api/v1/profile.py`
- Test: `backend/tests/test_sessions_api.py`

**Interfaces:**
- Consumes: `sessions.list_active/revoke/revoke_others` (Task 2), `get_current_session`/`get_current_user` (Task 3).
- Produces: `GET /profile/sessions -> list[SessionOut]`; `DELETE /profile/sessions/{id} -> Message`; `POST /profile/sessions/revoke-others -> Message`.

- [ ] **Step 1: Write failing tests** — `backend/tests/test_sessions_api.py`

```python
def _login(client, make_user, name="rr"):
    make_user(name, "Recruit123!")
    r = client.post("/api/v1/auth/login", json={"username": name, "password": "Recruit123!"})
    j = r.json()
    return {"Authorization": f"Bearer {j['access_token']}"}


def test_list_sessions_marks_current_and_hides_sid(client, make_user):
    h = _login(client, make_user)
    r = client.get("/api/v1/profile/sessions", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["current"] is True
    assert "sid" not in rows[0]


def test_revoke_other_session_signs_it_out(client, make_user):
    h1 = _login(client, make_user, "userA")
    # a second login for the same user = a second session
    r2 = client.post("/api/v1/auth/login", json={"username": "userA", "password": "Recruit123!"})
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    rows = client.get("/api/v1/profile/sessions", headers=h1).json()
    other = next(s for s in rows if not s["current"])
    assert client.delete(f"/api/v1/profile/sessions/{other['id']}", headers=h1).status_code == 200
    # the revoked session's token is now dead
    assert client.get("/api/v1/auth/me", headers=h2).status_code == 401


def test_cannot_revoke_another_users_session(client, make_user):
    h1 = _login(client, make_user, "owner")
    hx = _login(client, make_user, "intruder")
    sid_row = client.get("/api/v1/profile/sessions", headers=h1).json()[0]
    assert client.delete(f"/api/v1/profile/sessions/{sid_row['id']}", headers=hx).status_code == 404


def test_revoke_others_keeps_current(client, make_user):
    h1 = _login(client, make_user, "multi")
    client.post("/api/v1/auth/login", json={"username": "multi", "password": "Recruit123!"})
    client.post("/api/v1/auth/login", json={"username": "multi", "password": "Recruit123!"})
    r = client.post("/api/v1/profile/sessions/revoke-others", headers=h1)
    assert r.status_code == 200
    rows = client.get("/api/v1/profile/sessions", headers=h1).json()
    assert len(rows) == 1 and rows[0]["current"] is True
```

- [ ] **Step 2: Run, verify it fails** — `uv run pytest tests/test_sessions_api.py -q` → 404 (routes absent).

- [ ] **Step 3: Add `SessionOut`** — `backend/app/schemas/profile.py`

```python
class SessionOut(BaseModel):
    """An active signed-in device/session. `sid` is intentionally never exposed."""

    id: int
    device_label: str
    ip_address: str | None = None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool = False
```

- [ ] **Step 4: Add the routes** — `backend/app/api/v1/profile.py` (import `AuthSession`, `get_current_session`, `sessions`, `SessionOut`)

```python
@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    current: AuthSession = Depends(get_current_session),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionOut]:
    return [
        SessionOut(
            id=s.id, device_label=s.device_label, ip_address=s.ip_address,
            created_at=s.created_at, last_seen_at=s.last_seen_at, expires_at=s.expires_at,
            current=(s.sid == current.sid),
        )
        for s in sessions.list_active(db, user)
    ]


@router.delete("/sessions/{session_id}", response_model=Message)
def revoke_session(
    session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    if not sessions.revoke(db, user, session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Message(detail="Signed out that device")


@router.post("/sessions/revoke-others", response_model=Message)
def revoke_other_sessions(
    current: AuthSession = Depends(get_current_session),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    n = sessions.revoke_others(db, user, current.sid)
    return Message(detail=f"Signed out {n} other device(s)")
```

- [ ] **Step 5: Run, verify pass** — `uv run pytest tests/test_sessions_api.py -q` → PASS.

- [ ] **Step 6: Commit** — `git commit -am "feat(sessions): profile sessions list + revoke endpoints"`

---

### Task 6: admin revoke-sessions

**Files:**
- Modify: `backend/app/api/v1/admin.py`
- Test: `backend/tests/test_admin.py` (append one test)

**Interfaces:**
- Consumes: `sessions.revoke_all` (Task 2).
- Produces: `POST /admin/users/{user_id}/revoke-sessions -> Message`.

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_admin.py`

```python
def test_admin_revoke_sessions(client, admin_user, auth_headers, make_user):
    target = make_user("target", "Recruit123!")
    client.post("/api/v1/auth/login", json={"username": "target", "password": "Recruit123!"})
    r = client.post(f"/api/v1/admin/users/{target.id}/revoke-sessions", headers=auth_headers)
    assert r.status_code == 200
    assert "device" in r.json()["detail"]
```

- [ ] **Step 2: Run, verify fail** — `uv run pytest tests/test_admin.py -q -k revoke_sessions` → 404.

- [ ] **Step 3: Add the route** — `backend/app/api/v1/admin.py` (import `sessions`; mirror `admin_revoke_trusted_devices`)

```python
@router.post("/users/{user_id}/revoke-sessions", response_model=Message)
def admin_revoke_sessions(
    user_id: int,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Message:
    user = _get_or_404(db, user_id)
    n = sessions.revoke_all(db, user)
    record_activity(
        db, user=actor, action="UPDATE", table_name="users",
        record_id=user.id, record_description=user.username,
        details="revoked sessions", request=request,
    )
    return Message(detail=f"Signed out {n} device(s)")
```

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_admin.py -q -k revoke_sessions` → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat(sessions): admin revoke-sessions endpoint"`

---

### Task 7: web API client methods

**Files:**
- Modify: `web/src/lib/api.ts`
- Test: `web/src/lib/api.sessions.test.ts`

**Interfaces:**
- Produces: `api.listSessions()`, `api.revokeSession(id)`, `api.revokeOtherSessions()`; exported `SessionOut` type.

- [ ] **Step 1: Write the failing test** — `web/src/lib/api.sessions.test.ts` (mirror `api.profile2fa.test.ts`; check the endpoints + methods used). Example shape:

```ts
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status < 400, status,
    json: async () => body,
  } as Response);
}

beforeEach(() => localStorage.setItem("det695.access", "t"));

describe("sessions api", () => {
  it("lists sessions", async () => {
    const rows = [{ id: 1, device_label: "Chrome on macOS", current: true,
      created_at: "x", last_seen_at: "x", expires_at: "x", ip_address: null }];
    global.fetch = mockFetch(200, rows);
    const out = await api.listSessions();
    expect(out[0].current).toBe(true);
    expect((global.fetch as any).mock.calls[0][0]).toContain("/profile/sessions");
  });

  it("revokes a session with DELETE", async () => {
    global.fetch = mockFetch(200, { detail: "ok" });
    await api.revokeSession(5);
    const [url, opts] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/profile/sessions/5");
    expect(opts.method).toBe("DELETE");
  });

  it("revokes others with POST", async () => {
    global.fetch = mockFetch(200, { detail: "ok" });
    await api.revokeOtherSessions();
    const [url, opts] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/profile/sessions/revoke-others");
    expect(opts.method).toBe("POST");
  });
});
```

- [ ] **Step 2: Run, verify fail** — `cd web && npx vitest run src/lib/api.sessions.test.ts` → FAIL (methods undefined).

- [ ] **Step 3: Add the type + methods** — `web/src/lib/api.ts`. Near the `TokenPair` local type, add:

```ts
// Local structural type (the OpenAPI generator isn't re-run for this client;
// see TokenPair above for the same pattern).
export type SessionOut = {
  id: number;
  device_label: string;
  ip_address: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  current: boolean;
};
```
and inside the `api` object (next to the trusted-device methods):
```ts
  listSessions: () => request<SessionOut[]>("/profile/sessions"),
  revokeSession: (id: number) => request<void>(`/profile/sessions/${id}`, { method: "DELETE" }),
  revokeOtherSessions: () => request<void>("/profile/sessions/revoke-others", { method: "POST" }),
```

- [ ] **Step 4: Run, verify pass** — `npx vitest run src/lib/api.sessions.test.ts` → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat(web): sessions api client methods"`

---

### Task 8: "Signed-in devices" card on Profile

**Files:**
- Modify: `web/src/pages/Profile.tsx` (add `SignedInDevicesCard`, render it always)
- Modify: `web/src/pages/Profile.module.css` (row styles)

**Interfaces:**
- Consumes: `api.listSessions/revokeSession/revokeOtherSessions`, `SessionOut` (Task 7).

- [ ] **Step 1: Add the card component** — `web/src/pages/Profile.tsx` (after `TrustedDevicesCard`). It always renders (not gated on 2FA).

```tsx
/* ---- Signed-in devices (active sessions): list + per-row / bulk sign-out ---- */
function SignedInDevicesCard({ notify }: { notify: (k: "ok" | "error", m: string) => void }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["sessions"], queryFn: () => api.listSessions() });
  const revoke = useMutation({
    mutationFn: (id: number) => api.revokeSession(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sessions"] }); notify("ok", "Signed that device out."); },
    onError: (e) => notify("error", errMsg(e, "Couldn't sign out that device.")),
  });
  const revokeOthers = useMutation({
    mutationFn: () => api.revokeOtherSessions(),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sessions"] }); notify("ok", "Signed out your other devices."); },
    onError: (e) => notify("error", errMsg(e, "Couldn't sign out the other devices.")),
  });
  const sessions = q.data ?? [];

  return (
    <section className={`card ${styles.panel}`}>
      <div className={styles.panelHead}>
        <div>
          <h2 className={styles.panelTitle}>Signed-in devices</h2>
          <span className={styles.panelNote}>Devices currently signed in to your account. Sign out any you don't recognize.</span>
        </div>
      </div>
      {q.isLoading ? (
        <div className={styles.skeleton} style={{ height: 72, borderRadius: "var(--r-md)" }} />
      ) : sessions.length === 0 ? (
        <p className={styles.note}>No active sessions.</p>
      ) : (
        <ul className={styles.stack} style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {sessions.map((s) => (
            <li key={s.id} className={styles.field}>
              <div className={styles.fieldValue}>
                {s.device_label}{" "}
                {s.current && <span className={`${styles.badge} ${styles.badgeOn}`}><span className={styles.badgeDot} aria-hidden />This device</span>}
              </div>
              <span className={styles.panelNote}>
                {s.ip_address ? `${s.ip_address} · ` : ""}Last active {new Date(s.last_seen_at).toLocaleString()}
              </span>
              {!s.current && (
                <div className={styles.actions} style={{ justifyContent: "flex-start", marginTop: "var(--sp-2)" }}>
                  <button className="btn btn-ghost" onClick={() => revoke.mutate(s.id)} disabled={revoke.isPending}>Sign out</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {sessions.length > 1 && (
        <div className={styles.actions}>
          <button className="btn btn-ghost" onClick={() => revokeOthers.mutate()} disabled={revokeOthers.isPending}>
            {revokeOthers.isPending ? "Signing out…" : "Sign out all other devices"}
          </button>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Render it** — in the `Profile` component's success branch, add `<SignedInDevicesCard notify={notify} />` after `<TwoFactorCard .../>` (before the 2FA-gated `TrustedDevicesCard`):

```tsx
          <ProfileCard user={user} notify={notify} />
          <PasswordCard notify={notify} />
          <TwoFactorCard notify={notify} />
          <SignedInDevicesCard notify={notify} />
          {twoFAQ.data?.enabled && <TrustedDevicesCard />}
```

- [ ] **Step 3: Verify build + typecheck** — `cd web && npx tsc --noEmit && npx vitest run` → green (no new test required here; covered by api test + manual). Optionally add a light component test if the harness has RTL.

- [ ] **Step 4: Commit** — `git commit -am "feat(web): signed-in devices card on profile"`

---

### Task 9: 2FA on/off toggle + fix ripped backend tests

**Files:**
- Modify: `web/src/pages/Profile.tsx` (`TwoFactorCard` → toggle)
- Modify: `web/src/pages/Profile.module.css` (`.switch`)
- Modify: any backend test that logs out without auth or mints tokens without a session

**Interfaces:** unchanged API; UI only, plus test fixes.

- [ ] **Step 1: Backend ripple audit** — run the FULL suite: `cd backend && uv run pytest -q`. Expect failures only where a test (a) calls `/auth/logout` without an `Authorization` header, or (b) mints an access token via `create_access_token(...)` and calls a protected route without seeding a matching `AuthSession`. For each: add the auth header (logout) or seed a session (see `test_sessions_auth._seed_user_and_session` pattern). Do **not** weaken `get_current_user`. Re-run until green. Record which files changed in the commit message.

- [ ] **Step 2: Add switch CSS** — `web/src/pages/Profile.module.css` (append)

```css
/* ---- Toggle switch ---- */
.switch { position: relative; display: inline-flex; align-items: center; }
.switch input { position: absolute; opacity: 0; width: 44px; height: 24px; margin: 0; cursor: pointer; }
.switchTrack {
  width: 44px; height: 24px; border-radius: 999px; background: var(--surface-2);
  border: 1px solid var(--border); transition: background 0.15s ease; position: relative;
}
.switchTrack::after {
  content: ""; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px;
  border-radius: 50%; background: var(--surface); box-shadow: var(--shadow-1); transition: transform 0.15s ease;
}
.switch input:checked + .switchTrack { background: var(--ok); border-color: var(--ok); }
.switch input:checked + .switchTrack::after { transform: translateX(20px); }
.switch input:disabled + .switchTrack { opacity: 0.6; cursor: default; }
```

- [ ] **Step 3: Rewrite `TwoFactorCard`'s control** — keep the existing queries/mutations (`statusQ`, `enroll`, `verify`, `disable`, `awaitingCode`, `code`). Replace the header's badge and the enabled/awaiting/disabled button branches so the primary control is a switch. The switch is checked when `enabled || awaitingCode`; toggling from off calls `enroll.mutate()`, toggling from on calls `disable.mutate()`. Keep the inline themed code form for the `awaitingCode` step (it already uses `styles.codeInput`). Concretely, replace the `panelHead` trailing badge with the switch and drop the standalone "Enable email 2FA" / "Turn off" buttons:

```tsx
      <div className={styles.panelHead}>
        <div>
          <h2 className={styles.panelTitle}>Two-factor authentication</h2>
          <span className={styles.panelNote}>Get a one-time code by email on top of your password.</span>
        </div>
        {!statusQ.isLoading && (
          <label className={styles.switch} title={enabled ? "Turn off" : "Turn on"}>
            <input
              type="checkbox"
              role="switch"
              checked={enabled || awaitingCode}
              disabled={enroll.isPending || disable.isPending || verify.isPending}
              onChange={(e) => {
                if (e.target.checked) { if (!enabled) enroll.mutate(); }
                else if (enabled) disable.mutate();
                else { setAwaitingCode(false); setCode(""); }
              }}
              aria-label="Email two-factor authentication"
            />
            <span className={styles.switchTrack} aria-hidden />
          </label>
        )}
      </div>
```
Then the body: keep the `awaitingCode` inline verify form (Cancel sets `awaitingCode=false`), keep the enabled explanatory `note`, and for the disabled state show just the explanatory `note` (no button — the switch is the control). Remove the now-unused `btn-accent` / `btn-ghost` action rows for enable/turn-off.

- [ ] **Step 4: Verify** — `cd web && npx tsc --noEmit && npx vitest run`; `cd backend && uv run pytest -q` both green.

- [ ] **Step 5: Commit** — `git commit -am "feat(web): 2FA on/off toggle; fix session-ripple backend tests"`

---

### Task 10: non-blocking enrollment banner (replace the modal)

**Files:**
- Create: `web/src/components/EnrollmentBanner.tsx`
- Modify: `web/src/components/AppShell.tsx`
- Delete: `web/src/components/EnrollmentPrompt.tsx`

**Interfaces:**
- Consumes: `useAuth()` (`user`, `refresh`), `api.twoFAEnrollmentDismiss`, `react-router` `useNavigate`.

- [ ] **Step 1: Create the banner** — `web/src/components/EnrollmentBanner.tsx`

```tsx
/* Non-blocking first-login nudge to turn on email 2FA. A dismissible strip at
   the top of the app — never grays out or traps the page. "Turn on" routes to
   Profile (where the themed toggle + code entry live); "Not now" dismisses for
   good. Shown once, only for a user who hasn't enabled 2FA and hasn't been
   prompted. */
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import styles from "./EnrollmentBanner.module.css";

export function EnrollmentBanner() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const dismiss = useMutation({
    mutationFn: () => api.twoFAEnrollmentDismiss(),
    onSuccess: () => { void refresh(); },
  });

  if (!user || user.two_factor_enabled || user.two_factor_enrollment_prompted) return null;

  return (
    <div className={styles.banner} role="region" aria-label="Two-factor setup">
      <span className={styles.text}>
        Add an email code at sign-in for extra security on your account.
      </span>
      <div className={styles.actions}>
        <button className="btn btn-ghost" onClick={() => dismiss.mutate()} disabled={dismiss.isPending}>
          {dismiss.isPending ? "Dismissing…" : "Not now"}
        </button>
        <button className="btn btn-primary" onClick={() => navigate("/profile")}>Turn on</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `web/src/components/EnrollmentBanner.module.css`**

```css
.banner {
  display: flex; align-items: center; justify-content: space-between; gap: var(--sp-4);
  padding: var(--sp-3) var(--sp-4); margin-bottom: var(--sp-4);
  border: 1px solid var(--border); border-radius: var(--r-md);
  background: color-mix(in srgb, var(--accent, #b98a2e) 10%, var(--surface));
  color: var(--ink); font-size: var(--t-sm);
}
.text { flex: 1; }
.actions { display: flex; gap: var(--sp-3); flex: none; }
@media (max-width: 620px) { .banner { flex-direction: column; align-items: stretch; } }
```
(If `--accent` isn't defined in `index.css`, use `var(--surface-2)` instead.)

- [ ] **Step 3: Wire into AppShell** — `web/src/components/AppShell.tsx`: replace `import { EnrollmentPrompt } from "./EnrollmentPrompt";` with `import { EnrollmentBanner } from "./EnrollmentBanner";`, remove `<EnrollmentPrompt />` at the end, and render `<EnrollmentBanner />` at the top of `<main className={styles.content}>`, before `<Outlet />`:

```tsx
        <main className={styles.content}>
          <EnrollmentBanner />
          <Outlet />
        </main>
```

- [ ] **Step 4: Delete the modal** — `git rm web/src/components/EnrollmentPrompt.tsx`. Grep for other imports of it (`grep -rn EnrollmentPrompt web/src`) and remove/replace any.

- [ ] **Step 5: Verify** — `cd web && npx tsc --noEmit && npx vitest run` green.

- [ ] **Step 6: Commit** — `git commit -am "feat(web): non-blocking 2FA enrollment banner; remove blocking modal"`

---

### Task 11: theme the login code box

**Files:**
- Modify: `web/src/index.css` (add `.otp-input`)
- Modify: `web/src/pages/LoginVerify.tsx`

- [ ] **Step 1: Add a themed utility** — `web/src/index.css` (near other input styles)

```css
.otp-input {
  font-family: var(--font-mono);
  letter-spacing: 0.4em;
  text-align: center;
  max-width: 220px;
}
```

- [ ] **Step 2: Apply it** — `web/src/pages/LoginVerify.tsx`: change the code `<input>`'s `className="input"` to `className="input otp-input"`; center the card (`margin: "10vh auto"` already fine). No logic change.

- [ ] **Step 3: Verify** — `cd web && npx tsc --noEmit && npx vitest run src/pages/LoginVerify.test.tsx` green.

- [ ] **Step 4: Commit** — `git commit -am "style(web): theme the sign-in code input"`

---

### Task 12: restore-drill + backups doc (14 tables)

**Files:**
- Modify: `.github/workflows/restore-drill.yml:103`
- Modify: `wiki/Backups-and-Recovery.md`

- [ ] **Step 1: Add `auth_sessions` to EXPECTED** — `.github/workflows/restore-drill.yml` line 103, insert `auth_sessions` at the front of the space-separated list (keep alphabetical): `EXPECTED="activity_log auth_sessions cadet external_link follow_up intake_settings password_history potential_recruit recruit_stage_event recruitment_document recruitment_event trusted_devices university_contact users"`.

- [ ] **Step 2: Bump the wiki counts** — `wiki/Backups-and-Recovery.md`: change "all 13 tables present" → "all 14 tables present" (CHECK node) and "all 13 expected tables (including trusted_devices for email 2FA)" → "all 14 expected tables (including trusted_devices and auth_sessions)".

- [ ] **Step 3: Commit** — `git commit -am "ci(backups): cover auth_sessions in the restore drill"`

---

### Task 13: docs — Database, Testing, READMEs

**Files:**
- Modify: `wiki/Database.md`, `wiki/Testing.md`, `README.md`, `backend/README.md`

- [ ] **Step 1: Database.md** — bump the table count ("12 tables" → "13"), add an `AUTH_SESSIONS` entity to the ER block with its columns and a `USERS ||--o{ AUTH_SESSIONS` relationship, and add the `auth_sessions` row to the table list. Match the existing `trusted_devices` entries' formatting.

- [ ] **Step 2: Testing.md** — after the suite runs green (Task 14), update the pytest badge count and the "N tests across M files" line to the actual numbers, and add a bullet under Auth/Profile: "**Sessions** — a login creates a revocable server-side session; revoking (self, others, admin) or logout signs that device out immediately; `sid`-less tokens are rejected."

- [ ] **Step 3: READMEs** — update the test-count badges in `README.md` and `backend/README.md` to the new totals; if the stack line enumerates security features, add "revocable sessions".

- [ ] **Step 4: Commit** — `git commit -am "docs: session tracking in Database/Testing/README"`

---

### Task 14: full verification + counts

**Files:** none (verification), then fold final counts into Task 13 docs if not already exact.

- [ ] **Step 1: Backend suite** — `cd backend && uv run pytest -q` → all green. Note the total count.
- [ ] **Step 2: Backend lint** — `uv run ruff check app tests` → clean (fix any import-order/unused issues introduced).
- [ ] **Step 3: Web typecheck + tests** — `cd web && npx tsc --noEmit && npx vitest run` → green.
- [ ] **Step 4: Web build** — `npx vite build` (or the repo's `npm run build`) → succeeds.
- [ ] **Step 5: Reconcile doc counts** — if the pytest total differs from what Task 13 wrote, correct the numbers in `Testing.md` / READMEs. Commit any fixups.
- [ ] **Step 6: Final commit** — `git commit -am "test: verify session tracking + 2FA UX end-to-end" --allow-empty`

---

## Deploy (after the finishing skill merges to main)

1. **Migration first (additive):** against the **direct** (non-`-pooler`) Neon host —
   `cd backend && DATABASE_URL="<direct url>" uv run alembic upgrade head`. Verify `auth_sessions` exists and the 2 users are intact.
2. **Push** `main` to `origin/main` → Vercel builds + deploys.
3. Everyone re-logs in once (old `sid`-less tokens rejected). Verify: sign in, open Profile → "Signed-in devices" shows the current device; sign out from a second browser and confirm it drops.
4. Confirm `RESEND_API_KEY` / `RESEND_FROM_EMAIL` are set in Vercel (unrelated to sessions, but required for the 2FA emails to actually send).

## Self-Review Notes

- **Spec coverage:** sessions store (T1-6), web view+revoke (T7-8), toggle (T9), banner (T10), code theme (T11), backups/docs (T12-13), verify (T14). ✅
- **Type consistency:** `AuthSession.sid`/`SessionOut.current` used consistently; `_issue_token_pair(user, sid)` signature matches all three call sites; `create_refresh_token(subject, extra)` matches Task 3+4. ✅
- **Ripple flagged:** Task 9 Step 1 explicitly audits existing tests broken by the `sid` requirement — the one non-obvious risk. ✅
