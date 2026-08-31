"""Application configuration, loaded from environment / .env."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Signing key sentinel: the only acceptable use is local dev. If this value is
# still in effect on a deployed (Vercel) environment the app would silently sign
# every JWT with a publicly-known string, so we refuse to boot — see the
# model validator below.
INSECURE_SECRET_KEY_DEFAULT = "dev-only-insecure-change-me"


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

    @model_validator(mode="after")
    def _require_real_secret_key_in_deploy(self):
        # Vercel sets VERCEL=1 in every deployed runtime (prod & preview). If the
        # insecure default is still in effect there, fail fast rather than sign
        # forgeable tokens. Local dev / tests (no VERCEL var) are unaffected.
        if self.secret_key == INSECURE_SECRET_KEY_DEFAULT and os.environ.get("VERCEL"):
            raise ValueError(
                "SECRET_KEY is unset (still the insecure default) in a deployed "
                "environment. Set SECRET_KEY in the Vercel dashboard before deploying."
            )
        return self

    # Security
    secret_key: str = INSECURE_SECRET_KEY_DEFAULT
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

    # File uploads. Documents are stored as bytea in Postgres (see
    # app/api/v1/materials.py) — they rarely change and this keeps them inside
    # the nightly pg_dump backup. No external blob store.
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Cron / backup auth
    cron_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Email (Resend) — REQUIRED in production for intake acknowledgments.
    # Empty disables sending (local/dev): submissions still succeed, emails are skipped.
    resend_api_key: str = ""
    resend_from_email: str = ""  # must be on a domain verified in Resend

    # 2FA — email one-time code
    otp_code_length: int = 6
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_resends: int = 3

    # Trusted devices (skip the 2FA code on a known device)
    trusted_device_ttl_days: int = 30
    trusted_device_cookie_name: str = "det695_trust"

    # Per-IP throttle on unauthenticated auth endpoints (login / reset / forgot).
    # A backstop against lockout-DoS and credential brute-force: any single IP
    # is capped at this many attempts per window. The per-account lockout still
    # applies on top. Sized well above any legitimate burst.
    auth_rate_limit_max: int = 20
    auth_rate_limit_window_minutes: int = 15

    # Refresh token is delivered to browser clients as an httponly cookie (the
    # token is never persisted in JS-readable storage). Native clients (iOS)
    # continue to use the refresh_token in the response body + request body.
    refresh_cookie_name: str = "det695_refresh"

    # Cloudflare Turnstile secret (server-side verify). Empty disables verification
    # (local/dev) — set in production so the public form is bot-protected.
    turnstile_secret_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
