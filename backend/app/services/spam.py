"""Public-form abuse defenses: Cloudflare Turnstile + a loose IP rate-limit.

Turnstile is the PRIMARY bot defense. The IP rate-limit is only a high
threshold backstop — a recruiting table or classroom on shared WiFi shares one
NAT'd IP, so a low cap would reject legitimate recruits.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.net import client_ip
from app.core.security import now_utc
from app.models import PotentialRecruit

logger = logging.getLogger("afrotc695.spam")

_SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
RATE_LIMIT_PER_HOUR = 30

# ``client_ip`` is re-exported from app.core.net so existing callers
# (``from app.services.spam import client_ip``) keep working. Vercel overwrites
# X-Forwarded-For to prevent spoofing; the helper prefers the non-overwritable
# x-vercel-forwarded-for header. See app/core/net.py.
__all__ = ["client_ip", "too_many_from_ip", "verify_turnstile", "RATE_LIMIT_PER_HOUR"]


def verify_turnstile(token: str, remote_ip: str | None) -> bool:
    if not settings.turnstile_secret_key:
        logger.warning("TURNSTILE_SECRET_KEY unset; skipping verification (dev mode).")
        return True
    if not token:
        return False
    try:
        resp = httpx.post(
            _SITEVERIFY_URL,
            data={
                "secret": settings.turnstile_secret_key,
                "response": token,
                "remoteip": remote_ip or "",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return bool(resp.json().get("success"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Turnstile verify failed: %s", exc)
        return False


def too_many_from_ip(db: Session, ip: str | None) -> bool:
    if not ip:
        return False
    since = now_utc() - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(PotentialRecruit)
        .where(PotentialRecruit.source_ip == ip, PotentialRecruit.created_at >= since)
    ) or 0
    return count >= RATE_LIMIT_PER_HOUR
