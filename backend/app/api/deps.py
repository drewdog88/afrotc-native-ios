"""Shared FastAPI dependencies: DB session, current user, admin gate, paging."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise _UNAUTHORIZED
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise _UNAUTHORIZED
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise _UNAUTHORIZED from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required"
        )
    return user


def require_write(user: User = Depends(get_current_user)) -> User:
    """Gate for data mutations: admins and recruiters pass, viewers are blocked.

    Sign-in, password changes, and a user's own profile/2FA stay open — this
    only guards create/edit/delete of recruiting data, so a read-only viewer
    can still log in and manage their own account.
    """
    if user.role == UserRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only account: contact a recruiter or administrator to make changes.",
        )
    return user


@dataclass
class Pagination:
    skip: int
    limit: int


def pagination(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Pagination:
    return Pagination(skip=skip, limit=limit)
