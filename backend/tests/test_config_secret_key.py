"""The SECRET_KEY startup guard (app/core/config.py)."""
import pytest
from pydantic import ValidationError

from app.core.config import INSECURE_SECRET_KEY_DEFAULT, Settings

_DB = "postgresql+psycopg://test:test@localhost:5432/test"


def test_insecure_default_on_vercel_refuses_to_boot(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(secret_key=INSECURE_SECRET_KEY_DEFAULT, database_url=_DB)


def test_insecure_default_allowed_off_vercel(monkeypatch) -> None:
    monkeypatch.delenv("VERCEL", raising=False)
    s = Settings(secret_key=INSECURE_SECRET_KEY_DEFAULT, database_url=_DB)
    assert s.secret_key == INSECURE_SECRET_KEY_DEFAULT


def test_real_key_on_vercel_is_fine(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    s = Settings(secret_key="a-real-production-key", database_url=_DB)
    assert s.secret_key == "a-real-production-key"
