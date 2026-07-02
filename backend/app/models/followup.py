"""FollowUp — reminders/tasks tied to a recruit or contact."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.security import now_utc
from app.models.mixins import TimestampMixin


class FollowUpStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


class FollowUp(Base, TimestampMixin):
    __tablename__ = "follow_up"

    id: Mapped[int] = mapped_column(primary_key=True)
    note: Mapped[str] = mapped_column(Text)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default=FollowUpStatus.OPEN.value, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Who is responsible.
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Linked to a recruit and/or a contact (either may be null).
    recruit_id: Mapped[int | None] = mapped_column(
        ForeignKey("potential_recruit.id", ondelete="CASCADE"), nullable=True, index=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("university_contact.id", ondelete="CASCADE"), nullable=True, index=True
    )

    def mark_done(self) -> None:
        self.status = FollowUpStatus.DONE.value
        self.completed_at = now_utc()
