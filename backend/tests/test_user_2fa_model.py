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
