from datetime import timedelta
from types import SimpleNamespace

from app.core import security
from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole
from app.services import sessions
from tests.conftest import TestingSessionLocal


def _user(db, name="u"):
    u = User(
        username=name,
        email=f"{name}@det695.local",
        password_hash=hash_password("x"),
        first_name="A",
        last_name="B",
        role=UserRole.RECRUITER.value,
        is_active=True,
        password_expires_at=None,
        secret_question="q",
        secret_answer_hash=hash_password("a"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
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


def test_get_valid_none_for_missing_sid():
    with TestingSessionLocal() as db:
        assert sessions.get_valid(db, None) is None
        assert sessions.get_valid(db, "") is None
        assert sessions.get_valid(db, "not-a-real-sid") is None


def test_get_valid_none_for_revoked_session():
    with TestingSessionLocal() as db:
        user = _user(db)
        s = sessions.start(db, user, _req())
        assert sessions.revoke(db, user, s.id) is True
        assert sessions.get_valid(db, s.sid) is None


def test_get_valid_none_for_expired_session():
    with TestingSessionLocal() as db:
        user = _user(db)
        s = sessions.start(db, user, _req())
        s.expires_at = security.now_utc() - timedelta(days=1)
        db.commit()
        assert sessions.get_valid(db, s.sid) is None


def test_get_valid_returns_row_for_valid_session():
    with TestingSessionLocal() as db:
        user = _user(db)
        s = sessions.start(db, user, _req())
        found = sessions.get_valid(db, s.sid)
        assert found is not None
        assert found.id == s.id


def test_touch_advances_last_seen_at():
    with TestingSessionLocal() as db:
        user = _user(db)
        s = sessions.start(db, user, _req())
        old_last_seen = s.last_seen_at
        sessions.touch(db, s)
        assert s.last_seen_at >= old_last_seen


def test_revoke_all_revokes_every_active_session():
    with TestingSessionLocal() as db:
        user = _user(db)
        sessions.start(db, user, _req())
        sessions.start(db, user, _req())
        sessions.start(db, user, _req())
        n = sessions.revoke_all(db, user)
        assert n == 3
        assert sessions.list_active(db, user) == []
