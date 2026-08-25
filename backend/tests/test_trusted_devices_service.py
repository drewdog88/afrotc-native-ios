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


def test_revoke_own_device_sets_revoked_at(make_user: Callable[..., User]) -> None:
    user = make_user("td4")
    with TestingSessionLocal() as db:
        token = td.trust_device(db, user, "revokeme")
        row = db.query(TrustedDevice).one()
        assert td.revoke(db, user, row.id) is True
        db.refresh(row)
        assert row.revoked_at is not None
        assert td.find_valid(db, user, token) is None


def test_find_valid_none_for_revoked_device_with_correct_token(
    make_user: Callable[..., User]
) -> None:
    user = make_user("td5")
    with TestingSessionLocal() as db:
        token = td.trust_device(db, user, "willrevoke")
        row = db.query(TrustedDevice).one()
        assert td.find_valid(db, user, token) is not None
        assert td.revoke(db, user, row.id) is True
        assert td.find_valid(db, user, token) is None
