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
