"""ExternalLink + RecruitmentDocument (materials library)."""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ExternalLink(Base, TimestampMixin):
    __tablename__ = "external_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class RecruitmentDocument(Base, TimestampMixin):
    """Uploaded materials. File bytes live either in Postgres (`file_data`)
    or in Vercel Blob (`blob_url`), per STORAGE_BACKEND.
    """

    __tablename__ = "recruitment_document"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Storage: one of these is populated depending on STORAGE_BACKEND.
    blob_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
