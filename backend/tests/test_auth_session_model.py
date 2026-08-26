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
