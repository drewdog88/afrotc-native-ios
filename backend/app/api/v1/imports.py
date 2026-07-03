"""Bulk recruit import from CSV or Excel."""
from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import require_write
from app.core.database import get_db
from app.models import PotentialRecruit, RecruitStageEvent, User
from app.schemas.imports import ImportResult, ImportRowError
from app.schemas.recruit import RecruitCreate

router = APIRouter(prefix="/recruits", tags=["import"])


def _coerce_nan_to_none(row: dict) -> dict:
    """Replace pandas NaN/NaT values with None for Pydantic validation."""
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}


def _parse_file_to_dataframe(file: UploadFile) -> pd.DataFrame:
    """Parse uploaded CSV or Excel file into a pandas DataFrame."""
    content = file.file.read()
    filename = file.filename or ""
    content_type = file.content_type or ""

    # Determine parser based on extension or content-type
    if filename.endswith(".csv") or "csv" in content_type.lower():
        return pd.read_csv(io.BytesIO(content))
    elif filename.endswith((".xlsx", ".xls")) or "spreadsheet" in content_type.lower():
        return pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)",
        )


@router.post("/import", response_model=ImportResult)
def import_recruits(
    file: UploadFile = File(...),
    user: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> ImportResult:
    """Bulk import potential recruits from a CSV or Excel file.

    Each row is validated against RecruitCreate schema. Valid rows are imported
    with a baseline stage event; invalid rows are collected into an error report.
    """
    try:
        df = _parse_file_to_dataframe(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}",
        ) from e

    if df.empty:
        return ImportResult(total_rows=0, imported=0, failed=0, errors=[])

    total_rows = len(df)
    imported = 0
    errors: list[ImportRowError] = []

    for idx, row_data in df.iterrows():
        row_num = int(idx) + 1  # 1-indexed for user-facing error messages
        row_dict = _coerce_nan_to_none(row_data.to_dict())

        try:
            # Validate the row against RecruitCreate schema
            recruit_data = RecruitCreate(**row_dict)
        except ValidationError as ve:
            # Collect all validation errors for this row
            error_messages = [
                f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in ve.errors()
            ]
            errors.append(ImportRowError(row=row_num, errors=error_messages))
            continue
        except Exception as e:
            errors.append(ImportRowError(row=row_num, errors=[str(e)]))
            continue

        # Create the recruit record
        try:
            recruit = PotentialRecruit(**recruit_data.model_dump())
            db.add(recruit)
            db.flush()  # Flush to get the ID for the stage event

            # Add baseline stage event (mirrors create_recruit in recruits.py)
            db.add(
                RecruitStageEvent(
                    recruit_id=recruit.id,
                    from_stage=None,
                    to_stage=recruit.stage,
                    changed_by_id=user.id,
                    note="Bulk import",
                )
            )
            imported += 1
        except Exception as e:
            db.rollback()
            errors.append(ImportRowError(row=row_num, errors=[f"Database error: {str(e)}"]))
            continue

    # Commit all successfully validated and inserted recruits
    if imported > 0:
        db.commit()

    failed = len(errors)
    return ImportResult(total_rows=total_rows, imported=imported, failed=failed, errors=errors)
