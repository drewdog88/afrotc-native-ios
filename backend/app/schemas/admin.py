"""Admin schemas for user management and activity log."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole
from app.schemas.auth import UserOut
from app.schemas.common import ORMModel

__all__ = ["AdminUserCreate", "AdminUserUpdate", "ActivityLogOut", "UserOut"]


class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str | None = None
    role: UserRole = UserRole.RECRUITER
    secret_question: str
    secret_answer: str


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    is_locked: bool | None = None
    failed_login_attempts: int | None = None
    password: str | None = None


class ActivityLogOut(ORMModel):
    id: int
    user_id: int
    username: str
    action: str
    table_name: str | None = None
    record_id: int | None = None
    record_description: str | None = None
    details: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
