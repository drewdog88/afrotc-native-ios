"""UniversityContact + RecruitmentEvent."""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EventStatus
from app.models.mixins import TimestampMixin


class UniversityContact(Base, TimestampMixin):
    """A high-school / university point of contact (recruiting relationship)."""

    __tablename__ = "university_contact"

    id: Mapped[int] = mapped_column(primary_key=True)
    university_name: Mapped[str] = mapped_column(String(100))
    contact_name: Mapped[str] = mapped_column(String(100))
    contact_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Geocoding for the map view.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    events: Mapped[list[RecruitmentEvent]] = relationship(back_populates="university_contact")


class RecruitmentEvent(Base, TimestampMixin):
    __tablename__ = "recruitment_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    university_id: Mapped[int | None] = mapped_column(
        ForeignKey("university_contact.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default=EventStatus.SCHEDULED.value)
    attendees_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    university_contact: Mapped[UniversityContact | None] = relationship(back_populates="events")
