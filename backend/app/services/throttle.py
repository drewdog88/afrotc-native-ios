"""Per-IP throttle for the unauthenticated auth endpoints.

A DB-backed sliding-window limiter — deliberately not an in-process counter,
since the app runs as a Vercel serverless function where no per-instance state
survives between invocations. Each hit records a row; a hit is rejected once an
IP has exceeded the configured cap within the window. This is a backstop against
lockout-DoS and brute-force volume; the per-account lockout still applies.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import now_utc
from app.models import AuthAttempt
from app.services.spam import client_ip

_TOO_MANY = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many attempts. Please wait a few minutes and try again.",
)


def enforce(db: Session, request: Request, endpoint: str) -> None:
    """Record this attempt and raise 429 if the source IP is over the cap.

    Requests without a resolvable client IP are not throttled (nothing to key
    on) — they still face the per-account lockout.
    """
    ip = client_ip(request)
    if not ip:
        return

    since = now_utc() - timedelta(minutes=settings.auth_rate_limit_window_minutes)
    recent = db.scalar(
        select(func.count())
        .select_from(AuthAttempt)
        .where(
            AuthAttempt.ip_address == ip,
            AuthAttempt.endpoint == endpoint,
            AuthAttempt.created_at >= since,
        )
    ) or 0

    # Record the attempt regardless — a persistent flood keeps itself blocked
    # until its rows age out of the window.
    db.add(AuthAttempt(ip_address=ip[:45], endpoint=endpoint, created_at=now_utc()))
    db.commit()

    if recent >= settings.auth_rate_limit_max:
        raise _TOO_MANY
