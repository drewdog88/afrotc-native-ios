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
