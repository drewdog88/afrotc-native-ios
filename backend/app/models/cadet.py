"""Cadet."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import CadetStatus
from app.models.mixins import TimestampMixin


class Cadet(Base, TimestampMixin):
    __tablename__ = "cadet"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    major: Mapped[str] = mapped_column(String(100))
    graduation_year: Mapped[int] = mapped_column(Integer)
    cadet_rank: Mapped[str] = mapped_column(String(50))
    hometown: Mapped[str | None] = mapped_column(String(100), nullable=True)
    officer_interest: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=CadetStatus.ACTIVE.value, index=True)
    unenrollment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    unenrollment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
