"""Trusted-device tokens: a device that cleared 2FA may skip the code for a while."""
from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models import User
from app.models.trusted_device import TrustedDevice


def trust_device(db: Session, user: User, label: str) -> str:
    token = secrets.token_urlsafe(32)
    now = security.now_utc()
    db.add(
        TrustedDevice(
            user_id=user.id,
            token_hash=security.hash_token(token),
            device_label=(label or "")[:255],
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(days=settings.trusted_device_ttl_days),
        )
    )
    db.commit()
    return token


def find_valid(db: Session, user: User, token: str | None) -> TrustedDevice | None:
    if not token:
        return None
    row = db.scalar(
        select(TrustedDevice).where(
            TrustedDevice.user_id == user.id,
            TrustedDevice.token_hash == security.hash_token(token),
            TrustedDevice.revoked_at.is_(None),
        )
    )
    if row is None or row.expires_at <= security.now_utc():
        return None
    row.last_used_at = security.now_utc()
    db.commit()
    return row


def list_devices(db: Session, user: User) -> list[TrustedDevice]:
    return list(
        db.scalars(
            select(TrustedDevice)
            .where(TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None))
            .order_by(TrustedDevice.last_used_at.desc())
        )
    )


def revoke(db: Session, user: User, device_id: int) -> bool:
    row = db.get(TrustedDevice, device_id)
    if row is None or row.user_id != user.id or row.revoked_at is not None:
        return False
    row.revoked_at = security.now_utc()
    db.commit()
    return True


def revoke_all(db: Session, user: User, except_token: str | None = None) -> int:
    keep = security.hash_token(except_token) if except_token else None
    rows = db.scalars(
        select(TrustedDevice).where(
            TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None)
        )
    ).all()
    now = security.now_utc()
    count = 0
    for row in rows:
        if keep and row.token_hash == keep:
            continue
        row.revoked_at = now
        count += 1
    db.commit()
    return count
