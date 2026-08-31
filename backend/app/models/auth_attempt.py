"""Auth attempts — one row per hit on an unauthenticated auth endpoint.

Backs the per-IP throttle in ``app.services.throttle``. Rows are counted within
a sliding time window; old rows simply age out of that window (a periodic purge
is unnecessary at this app's volume).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuthAttempt(Base):
    __tablename__ = "auth_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(45), index=True)
    endpoint: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
