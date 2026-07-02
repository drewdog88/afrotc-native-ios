"""Export endpoints: CSV, XLSX, and PDF downloads for all entities."""
from __future__ import annotations

from datetime import date, time
from io import BytesIO
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    Cadet,
    PotentialRecruit,
    RecruitmentEvent,
    UniversityContact,
    User,
)

router = APIRouter(prefix="/export", tags=["export"])

EntityType = Literal["recruits", "cadets", "contacts", "events"]
FormatType = Literal["csv", "xlsx", "pdf"]

_ENTITY_MAP = {
    "recruits": PotentialRecruit,
    "cadets": Cadet,
    "contacts": UniversityContact,
    "events": RecruitmentEvent,
}


def _format_value(val):
    """Format value for export (handle dates, times, etc)."""
    if isinstance(val, (date, time)):
        return str(val)
    if val is None:
        return ""
    return val


def _get_dataframe(entity: EntityType, db: Session) -> pd.DataFrame:
    """Build a pandas DataFrame from entity rows."""
    model = _ENTITY_MAP[entity]
    rows = list(db.scalars(select(model)).all())

    if entity == "recruits":
        data = [
            {
                "ID": r.id,
                "First Name": r.first_name,
                "Last Name": r.last_name,
                "Email": r.email or "",
                "Phone": r.phone or "",
                "Major": r.major or "",
                "Current School": r.current_school,
                "School Type": r.school_type,
                "HS Graduation Year": r.high_school_graduation_year or "",
                "College Graduation Year": r.expected_college_graduation_year or "",
                "GPA": r.gpa or "",
                "SAT": r.sat_score or "",
                "ACT": r.act_score or "",
                "Stage": r.stage,
                "Interests": (r.interests or "")[:100],
                "Notes": (r.notes or "")[:100],
            }
            for r in rows
        ]
    elif entity == "cadets":
        data = [
            {
                "ID": c.id,
                "First Name": c.first_name,
                "Last Name": c.last_name,
                "Email": c.email,
                "Phone": c.phone or "",
                "Major": c.major,
                "Graduation Year": c.graduation_year,
                "Rank": c.cadet_rank,
                "Hometown": c.hometown or "",
                "Officer Interest": c.officer_interest or "",
                "Status": c.status,
                "GPA": c.gpa or "",
            }
            for c in rows
        ]
    elif entity == "contacts":
        data = [
            {
                "ID": ct.id,
                "University": ct.university_name,
                "Contact Name": ct.contact_name,
                "Title": ct.contact_title or "",
                "Email": ct.email,
                "Phone": ct.phone or "",
                "Address": (ct.address or "")[:100],
                "Active": "Yes" if ct.is_active else "No",
                "Notes": (ct.notes or "")[:100],
            }
            for ct in rows
        ]
    elif entity == "events":
        data = [
            {
                "ID": e.id,
                "Title": e.title,
                "Date": _format_value(e.event_date),
                "Start Time": _format_value(e.start_time),
                "End Time": _format_value(e.end_time),
                "Location": e.location or "",
                "Type": e.event_type,
                "Status": e.status,
                "Attendees": e.attendees_count,
                "Description": (e.description or "")[:100],
            }
            for e in rows
        ]
    else:
        data = []

    return pd.DataFrame(data)


@router.get("/{entity}")
def export_entity(
    entity: EntityType,
    format: FormatType,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export entity data in CSV, XLSX, or PDF format."""
    if entity not in _ENTITY_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown entity: {entity}",
        )

    if format not in ("csv", "xlsx", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown format: {format}",
        )

    df = _get_dataframe(entity, db)

    if format == "csv":
        buffer = BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={entity}.csv"
            },
        )

    elif format == "xlsx":
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=entity.capitalize())
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": f"attachment; filename={entity}.xlsx"
            },
        )

    elif format == "pdf":
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title = Paragraph(
            f"<b>{entity.capitalize()} Export</b>", styles["Heading1"]
        )
        elements.append(title)

        # Table data
        table_data = [df.columns.tolist()] + df.values.tolist()
        # Truncate long text in cells for PDF
        table_data = [
            [str(cell)[:50] for cell in row] for row in table_data
        ]

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                ]
            )
        )
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={entity}.pdf"
            },
        )

    # Should never reach here due to earlier validation
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected error in export",
    )
