"""Best-effort activity logging.

Writes an ``ActivityLog`` row for auditable actions (logins, user management,
Request-Info settings edits, recruit create/stage/delete). Mirrors the email
service's contract: an audit-write failure must never break the underlying
action, so every write is wrapped and swallowed with a warning. The entry is
committed on its own, so a caller that has already committed its main change
still gets the audit row.
"""
from __future__ import annotations

import logging

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.net import client_ip
from app.models import ActivityLog, User

logger = logging.getLogger("afrotc695.activity")


def _client_ip(request: Request | None) -> str | None:
    """Real client IP behind Vercel (see app/core/net.py), capped to the column.

    ``ip_address`` is a 45-char column (max INET6 text length), so truncate.
    """
    ip = client_ip(request)
    return ip[:45] if ip else None


def record_activity(
    db: Session,
    *,
    user: User | None = None,
    username: str | None = None,
    action: str,
    table_name: str | None = None,
    record_id: int | None = None,
    record_description: str | None = None,
    details: str | None = None,
    request: Request | None = None,
) -> None:
    """Record one activity-log entry. Best-effort — never raises.

    Pass ``user`` for a signed-in actor; for a public/system action (e.g. a
    public request-info submission) omit ``user`` and pass ``username`` as the
    human label (the row's ``user_id`` is then null).
    """
    try:
        ua = request.headers.get("user-agent") if request is not None else None
        entry = ActivityLog(
            user_id=user.id if user is not None else None,
            username=user.username if user is not None else (username or "system"),
            action=action,
            table_name=table_name,
            record_id=record_id,
            record_description=record_description,
            details=details,
            ip_address=_client_ip(request),
            user_agent=ua[:500] if ua else None,
        )
        db.add(entry)
        db.commit()
    except Exception:  # noqa: BLE001 — audit logging must never break the request
        db.rollback()
        logger.warning(
            "Failed to record activity (action=%s table=%s)",
            action,
            table_name,
            exc_info=True,
        )
