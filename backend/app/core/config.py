"""Application configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database — REQUIRED. Must be a PostgreSQL (Neon) connection string.
    # There is intentionally NO default and NO local/SQLite fallback: the
    # database lives only in Postgres so the pattern is unambiguous.
    database_url: str

    @field_validator("database_url")
    @classmethod
    def _require_postgres(cls, v: str) -> str:
        if not v or not v.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string "
                "(e.g. postgresql+psycopg://…). Local/SQLite databases are "
                "not permitted — there is no local fallback."
            )
        return v

    # Security
    secret_key: str = "dev-only-insecure-change-me"
    encryption_key: str = ""  # Fernet key for encrypting TOTP secrets at rest
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # Password policy
    password_expiry_days: int = 180
    max_failed_logins: int = 5
    password_history_size: int = 5

    # Bootstrap admin (seeded only if there are no users)
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_email: str = "admin@det695.local"
    bootstrap_admin_password: str = ""

    # File storage: "postgres" (bytea in DB) or "vercel_blob"
    storage_backend: str = "postgres"
    blob_read_write_token: str = ""
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Cron / backup auth
    cron_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
