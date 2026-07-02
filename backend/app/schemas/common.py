"""Shared schema building blocks: ORM base, pagination, error envelope."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response models read from SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """A paginated list response used by every list endpoint."""

    items: list[T]
    total: int
    skip: int
    limit: int


class Message(BaseModel):
    detail: str
