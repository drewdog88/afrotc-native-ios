"""Auth-session lifecycle: one row per login, revocable for remote sign-out."""
from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models import User
from app.models.auth_session import AuthSession
from app.services.activity import _client_ip


def _device_label(user_agent: str | None) -> str:
    """A short human label from the UA string; best-effort, never raises."""
    ua = user_agent or ""
    browser = next((b for b in ("Edg", "Chrome", "Firefox", "Safari") if b in ua), None)
    browser = {"Edg": "Edge"}.get(browser, browser)
    os_name = next((o for o, key in (("macOS", "Macintosh"), ("Windows", "Windows"),
                                     ("iPhone", "iPhone"), ("iPad", "iPad"),
                                     ("Android", "Android"), ("Linux", "Linux"))
                    if key in ua), None)
    if browser and os_name:
        return f"{browser} on {os_name}"
    if browser or os_name:
        return browser or os_name
    return (ua[:255] or "Unknown device")


def start(db: Session, user: User, request: Request) -> AuthSession:
    now = security.now_utc()
    ua = request.headers.get("user-agent") if request is not None else None
    row = AuthSession(
        user_id=user.id,
        sid=uuid.uuid4().hex,
        device_label=_device_label(ua)[:255],
        ip_address=_client_ip(request),
        user_agent=(ua[:500] if ua else None),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_valid(db: Session, sid: str | None) -> AuthSession | None:
    if not sid:
        return None
    row = db.scalar(select(AuthSession).where(AuthSession.sid == sid))
    if row is None or row.revoked_at is not None or row.expires_at <= security.now_utc():
        return None
    return row


def touch(db: Session, session: AuthSession) -> None:
    session.last_seen_at = security.now_utc()
    db.commit()


def list_active(db: Session, user: User) -> list[AuthSession]:
    now = security.now_utc()
    return list(db.scalars(
        select(AuthSession)
        .where(AuthSession.user_id == user.id,
               AuthSession.revoked_at.is_(None),
               AuthSession.expires_at > now)
        .order_by(AuthSession.last_seen_at.desc())
    ))


def revoke(db: Session, user: User, session_id: int) -> bool:
    row = db.get(AuthSession, session_id)
    if row is None or row.user_id != user.id or row.revoked_at is not None:
        return False
    row.revoked_at = security.now_utc()
    db.commit()
    return True


def revoke_others(db: Session, user: User, except_sid: str | None) -> int:
    rows = db.scalars(select(AuthSession).where(
        AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))).all()
    now = security.now_utc()
    n = 0
    for row in rows:
        if except_sid and row.sid == except_sid:
            continue
        row.revoked_at = now
        n += 1
    db.commit()
    return n


def revoke_all(db: Session, user: User) -> int:
    return revoke_others(db, user, except_sid=None)
