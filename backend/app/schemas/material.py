"""ExternalLink + RecruitmentDocument schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.schemas.common import ORMModel


class LinkBase(BaseModel):
    title: str
    url: HttpUrl
    description: str | None = None
    category: str = "general"
    is_active: bool = True
    sort_order: int = 0


class LinkCreate(LinkBase):
    pass


class LinkUpdate(BaseModel):
    title: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    category: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class LinkOut(ORMModel):
    id: int
    title: str
    url: str
    description: str | None = None
    category: str
    is_active: bool
    sort_order: int
    created_at: datetime
    last_modified: datetime


class DocumentOut(ORMModel):
    """Metadata for an uploaded document (NO raw bytes)."""

    id: int
    title: str
    description: str | None = None
    filename: str
    original_filename: str
    file_size: int | None = None
    file_type: str | None = None
    category: str
    is_active: bool
    sort_order: int
    created_at: datetime
    last_modified: datetime
