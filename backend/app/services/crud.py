"""Generic CRUD helper shared by every entity router.

Keeps list/search/pagination/get/create/update/delete uniform so each entity
router is thin and consistent. Entity-specific behavior (e.g. recruit stage
transitions) lives in the router on top of this base.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    def get(self, db: Session, obj_id: int) -> ModelType | None:
        return db.get(self.model, obj_id)

    def list(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        search_fields: tuple[str, ...] = (),
        filters: dict[str, Any] | None = None,
        order_by: Any = None,
    ) -> tuple[list[ModelType], int]:
        stmt = select(self.model)

        for field, value in (filters or {}).items():
            if value is not None and hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)

        if search and search_fields:
            like = f"%{search}%"
            clauses = [
                getattr(self.model, f).ilike(like)
                for f in search_fields
                if hasattr(self.model, f)
            ]
            if clauses:
                stmt = stmt.where(or_(*clauses))

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, "id"):
            stmt = stmt.order_by(self.model.id.desc())

        rows = list(db.scalars(stmt.offset(skip).limit(limit)).all())
        return rows, total

    def create(self, db: Session, data: dict[str, Any]) -> ModelType:
        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, obj: ModelType, data: dict[str, Any]) -> ModelType:
        for key, value in data.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, obj: ModelType) -> None:
        db.delete(obj)
        db.commit()
