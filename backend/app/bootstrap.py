"""First-run bootstrap: create the initial admin if the users table is empty."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole

logger = logging.getLogger("afrotc695.bootstrap")


def bootstrap_admin(db: Session) -> None:
    """Seed a single admin from env vars, only when no users exist.

    Replaces the old hardcoded admin/admin123 seed: the password comes from
    BOOTSTRAP_ADMIN_PASSWORD and the account is forced to change it on first login.
    """
    existing = db.scalar(select(User.id).limit(1))
    if existing is not None:
        return

    if not settings.bootstrap_admin_password:
        logger.warning(
            "No users exist and BOOTSTRAP_ADMIN_PASSWORD is unset; skipping admin bootstrap."
        )
        return

    admin = User(
        username=settings.bootstrap_admin_username,
        email=settings.bootstrap_admin_email,
        password_hash=hash_password(settings.bootstrap_admin_password),
        first_name="Detachment",
        last_name="Admin",
        role=UserRole.ADMIN.value,
        is_active=True,
        force_password_change=True,
        secret_question="Set this after first login",
        secret_answer_hash=hash_password("unset"),
    )
    db.add(admin)
    db.commit()
    logger.info("Bootstrapped admin user '%s' (must change password on first login).",
                settings.bootstrap_admin_username)
