"""PotentialRecruit + RecruitStageEvent (the funnel/trend backbone)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import now_utc
from app.models.enums import RecruitStage, SchoolType
from app.models.mixins import TimestampMixin


class PotentialRecruit(Base, TimestampMixin):
    __tablename__ = "potential_recruit"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    major: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_school: Mapped[str] = mapped_column(String(100))
    school_type: Mapped[str] = mapped_column(String(20), default=SchoolType.HIGH_SCHOOL.value)
    high_school_graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_college_graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    sat_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    act_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interests: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Funnel stage (replaces the old free-text `status`).
    stage: Mapped[str] = mapped_column(String(20), default=RecruitStage.LEAD.value, index=True)

    # Geocoding for the map view (derived from current_school/address).
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    stage_events: Mapped[list[RecruitStageEvent]] = relationship(
        back_populates="recruit",
        cascade="all, delete-orphan",
        order_by="RecruitStageEvent.changed_at",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class RecruitStageEvent(Base):
    """Immutable log of every stage transition — the source of truth for
    time-series funnel/conversion analytics. Never updated, only appended.
    """

    __tablename__ = "recruit_stage_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    recruit_id: Mapped[int] = mapped_column(
        ForeignKey("potential_recruit.id", ondelete="CASCADE"), index=True
    )
    from_stage: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, index=True
    )
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    recruit: Mapped[PotentialRecruit] = relationship(back_populates="stage_events")
