"""FollowUp (task/reminder) schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.followup import FollowUpStatus
from app.schemas.common import ORMModel


class FollowUpBase(BaseModel):
    note: str
    due_date: datetime
    assignee_id: int | None = None
    recruit_id: int | None = None
    contact_id: int | None = None


class FollowUpCreate(FollowUpBase):
    status: FollowUpStatus = FollowUpStatus.OPEN


class FollowUpUpdate(BaseModel):
    note: str | None = None
    due_date: datetime | None = None
    status: FollowUpStatus | None = None
    assignee_id: int | None = None
    recruit_id: int | None = None
    contact_id: int | None = None


class FollowUpOut(ORMModel):
    id: int
    note: str
    due_date: datetime
    status: str
    completed_at: datetime | None = None
    assignee_id: int | None = None
    created_by_id: int | None = None
    recruit_id: int | None = None
    contact_id: int | None = None
    created_at: datetime | None = None
    last_modified: datetime | None = None
