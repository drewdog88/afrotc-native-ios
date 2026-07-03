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
    """Uploaded materials. File bytes are stored in Postgres (`file_data`, bytea)
    so these rarely-changing documents stay inside the nightly pg_dump backup.
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

    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Legacy, unused: the old app kept an external blob URL here. Documents are
    # now stored in `file_data`; this column is always NULL and kept only to
    # avoid a production schema migration.
    blob_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
