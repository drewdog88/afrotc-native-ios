"""RecruitmentEvent schemas."""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel

from app.models.enums import EventStatus
from app.schemas.common import ORMModel


class EventBase(BaseModel):
    title: str
    description: str | None = None
    event_date: date
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = None
    university_id: int | None = None
    event_type: str
    attendees_count: int = 0
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class EventCreate(EventBase):
    status: EventStatus = EventStatus.SCHEDULED


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = None
    university_id: int | None = None
    event_type: str | None = None
    status: EventStatus | None = None
    attendees_count: int | None = None
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class EventOut(ORMModel):
    id: int
    title: str
    description: str | None = None
    event_date: date
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = None
    university_id: int | None = None
    event_type: str
    status: str
    attendees_count: int
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
