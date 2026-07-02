"""User, PasswordHistory, ActivityLog."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import now_utc
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.RECRUITER.value)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)

    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    password_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    force_password_change: Mapped[bool] = mapped_column(Boolean, default=False)

    # Account-recovery secret question
    secret_question: Mapped[str] = mapped_column(String(200))
    secret_answer_hash: Mapped[str] = mapped_column(String(255))

    # 2FA (TOTP). The secret is stored Fernet-encrypted at rest.
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    backup_codes_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_setup_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    can_enable_2fa: Mapped[bool] = mapped_column(Boolean, default=True)

    activity_logs: Mapped[list[ActivityLog]] = relationship(back_populates="user")
    password_history: Mapped[list[PasswordHistory]] = relationship(back_populates="user")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    @property
    def is_password_expired(self) -> bool:
        if self.is_admin or not self.password_expires_at:
            return False
        return now_utc() > self.password_expires_at

    @property
    def days_until_password_expiry(self) -> int | None:
        if self.is_admin or not self.password_expires_at:
            return None
        return max(0, (self.password_expires_at - now_utc()).days)

    @property
    def is_2fa_active(self) -> bool:
        return self.totp_enabled and self.totp_setup_completed


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped[User] = relationship(back_populates="password_history")


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    username: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(100))  # CREATE/UPDATE/DELETE/LOGIN/...
    table_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    record_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, index=True
    )

    user: Mapped[User] = relationship(back_populates="activity_logs")
