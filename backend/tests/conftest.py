"""Test harness for the FastAPI backend.

The app is Postgres-only at runtime (``config.py`` rejects any non-``postgresql``
``DATABASE_URL``) and its lifespan seeds an admin. Tests must not need a live
Postgres, so this conftest:

1. Sets a dummy ``postgresql`` ``DATABASE_URL`` (and a real ``ENCRYPTION_KEY``)
   *before* importing the app, so the config validator is satisfied. The real
   engine is created lazily and never connects because we never talk to it.
2. Points ``get_db`` at an in-memory SQLite database via a shared ``StaticPool``
   (one connection, so committed rows are visible across sessions).
3. Recreates the schema before every test (``Base.metadata.create_all``) — the
   app never owns DDL in production (Alembic does), but tests need tables.
4. Uses ``TestClient(app)`` *without* the context manager so the lifespan (and
   its bootstrap) never runs; tests seed the users they need themselves.
"""
from __future__ import annotations

import os

# --- Must happen before importing anything under app.* ---
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
# A valid Fernet key so TOTP encrypt/decrypt works in 2FA tests.
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1mZXJuZXQta2V5LTMyLWJ5dGVzLWxvbmchISE=")
# Empty on purpose: keeps bootstrap_admin a no-op if the lifespan ever runs.
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "")

from collections.abc import Callable, Iterator  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.api.v1.auth as auth_router  # noqa: E402
import app.core.database as database  # noqa: E402
import app.core.security as security  # noqa: E402
import app.main as main  # noqa: E402
import app.models  # noqa: E402,F401  (registers every model on Base.metadata)
import app.models.user as user_model  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.models.enums import UserRole  # noqa: E402


# SQLite drops tzinfo on round-trip, so a tz-aware value written by the app
# comes back naive and comparisons against ``now_utc()`` raise. Postgres keeps
# the tz, so this only bites tests. Make ``now_utc`` naive-UTC everywhere it is
# read at call time (model properties, the change-password expiry write) so the
# whole harness stays internally consistent.
def _naive_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


for _mod in (security, user_model, auth_router):
    _mod.now_utc = _naive_utc

# One shared in-memory SQLite connection for the whole session.
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE, autoflush=False, autocommit=False, future=True
)

# Belt-and-suspenders: if the lifespan ever runs, keep it on SQLite instead of
# trying to reach the dummy Postgres URL.
database.SessionLocal = TestingSessionLocal
main.SessionLocal = TestingSessionLocal


def _override_get_db() -> Iterator[Session]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Det695Demo!"


@pytest.fixture(autouse=True)
def _fresh_schema() -> Iterator[None]:
    """Give every test a clean database."""
    Base.metadata.create_all(TEST_ENGINE)
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture
def client() -> TestClient:
    # No context manager → lifespan/bootstrap does not run.
    return TestClient(app)


@pytest.fixture
def make_user() -> Callable[..., User]:
    """Factory that inserts a user directly and returns it.

    ``password_expires_at`` defaults to ``None`` so non-admin users never trip
    the tz-aware expiry comparison against SQLite's tz-naive datetimes.
    """

    def _make(
        username: str,
        password: str = "Recruit123!",
        *,
        role: UserRole = UserRole.RECRUITER,
        is_active: bool = True,
        force_password_change: bool = False,
        totp_secret: str | None = None,
        totp_enabled: bool = False,
        totp_setup_completed: bool = False,
    ) -> User:
        with TestingSessionLocal() as db:
            user = User(
                username=username,
                email=f"{username}@det695.local",
                password_hash=hash_password(password),
                first_name="Test",
                last_name=username.title(),
                role=role.value,
                is_active=is_active,
                force_password_change=force_password_change,
                password_expires_at=None,
                secret_question="Favorite squadron?",
                secret_answer_hash=hash_password("695"),
                totp_secret=totp_secret,
                totp_enabled=totp_enabled,
                totp_setup_completed=totp_setup_completed,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    return _make


@pytest.fixture
def admin_user(make_user: Callable[..., User]) -> User:
    return make_user(ADMIN_USERNAME, ADMIN_PASSWORD, role=UserRole.ADMIN)


def _login(client: TestClient, username: str, password: str, totp_code: str | None = None):
    body: dict[str, str] = {"username": username, "password": password}
    if totp_code is not None:
        body["totp_code"] = totp_code
    return client.post("/api/v1/auth/login", json=body)


@pytest.fixture
def auth_headers(client: TestClient, admin_user: User) -> dict[str, str]:
    """Authorization header for the seeded admin."""
    resp = _login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def login() -> Callable[..., object]:
    """Expose the login helper to tests that need custom credentials."""
    return _login
