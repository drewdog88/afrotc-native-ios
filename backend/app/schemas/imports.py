"""Bulk recruit import schemas."""
from __future__ import annotations

from pydantic import BaseModel


class ImportRowError(BaseModel):
    """Error details for a single row that failed validation/import."""

    row: int
    errors: list[str]


class ImportResult(BaseModel):
    """Summary result of a bulk import operation."""

    total_rows: int
    imported: int
    failed: int
    errors: list[ImportRowError]
