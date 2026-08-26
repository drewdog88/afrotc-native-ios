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
