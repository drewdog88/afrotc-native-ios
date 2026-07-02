"""Password hashing, JWT tokens, and TOTP-secret encryption."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt hashes at most the first 72 bytes of a password. We use the bcrypt
# library directly (passlib is unmaintained and incompatible with bcrypt 4.1+),
# and truncate to that limit explicitly so long inputs don't raise.
_BCRYPT_MAX_BYTES = 72


def now_utc() -> datetime:
    """Timezone-aware UTC now (project standard)."""
    return datetime.now(UTC)


# ---- Passwords ----
def _encode_password(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_encode_password(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---- JWT ----
def _create_token(
    subject: str,
    token_type: str,
    expires: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now_utc(),
        "exp": now_utc() + expires,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject, "access", timedelta(minutes=settings.access_token_expire_minutes), extra
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


# ---- TOTP-secret encryption (at rest) ----
def _fernet() -> Fernet | None:
    if not settings.encryption_key:
        return None
    try:
        return Fernet(settings.encryption_key.encode())
    except (ValueError, TypeError):
        return None


def encrypt_secret(plaintext: str) -> str:
    f = _fernet()
    if f is None:
        # Fail closed: never persist a TOTP secret unencrypted.
        raise RuntimeError("ENCRYPTION_KEY is not configured; cannot encrypt secret")
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str | None:
    f = _fernet()
    if f is None:
        return None
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None
