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


def test_resend_preserves_attempts(make_user: Callable[..., User]) -> None:
    user = make_user("otp6")
    otp.issue_code(user, "login")
    assert otp.verify_code(user, "000000", "login") is False
    assert user.otp_attempts == 1
    user.otp_last_sent_at = security.now_utc() - timedelta(seconds=61)
    assert otp.resend_code(user) is not None
    assert user.otp_attempts == 1


def test_can_resend_false_at_resend_cap(make_user: Callable[..., User]) -> None:
    user = make_user("otp7")
    otp.issue_code(user, "login")
    for _ in range(3):
        user.otp_last_sent_at = security.now_utc() - timedelta(seconds=61)
        assert otp.resend_code(user) is not None
    assert otp.can_resend(user) is False
