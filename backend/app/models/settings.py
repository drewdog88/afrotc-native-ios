"""Singleton configuration for the public request-info intake form."""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin

DEFAULT_ACK_SUBJECT = "Thanks for your interest in AFROTC Detachment 695"
DEFAULT_ACK_BODY = (
    "Hi {{first_name}},\n\n"
    "Thank you for your interest in Air Force ROTC Detachment 695. "
    "We received your information and a recruiter will reach out to you soon.\n\n"
    "In the meantime, you can learn more about the program here:\n"
    "https://www.afrotc.com\n\n"
    "Go forth and conquer,\n"
    "AFROTC Detachment 695"
)


class IntakeSettings(Base, TimestampMixin):
    """One row (id=1) holding admin-editable intake configuration."""

    __tablename__ = "intake_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    recruiter_notification_email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ack_email_subject: Mapped[str] = mapped_column(String(200), default=DEFAULT_ACK_SUBJECT)
    ack_email_body: Mapped[str] = mapped_column(Text, default=DEFAULT_ACK_BODY)
