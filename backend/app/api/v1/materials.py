"""Materials library: external links + uploaded documents."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, pagination
from app.core.config import settings
from app.core.database import get_db
from app.models import ExternalLink, RecruitmentDocument, User
from app.schemas.common import Page
from app.schemas.material import DocumentOut, LinkCreate, LinkOut, LinkUpdate
from app.services.crud import CRUDBase

router = APIRouter(prefix="/materials", tags=["materials"])

link_crud = CRUDBase(ExternalLink)
doc_crud = CRUDBase(RecruitmentDocument)

_LINK_SEARCH_FIELDS = ("title", "url", "description")
_DOC_SEARCH_FIELDS = ("title", "description", "filename")


def _secure_filename(filename: str) -> str:
    """Sanitize filename by removing path separators and dangerous chars."""
    name = os.path.basename(filename)
    name = name.replace("..", "")
    name = name.replace("/", "_")
    name = name.replace("\\", "_")
    return name or "unnamed"


def _get_link_or_404(db: Session, link_id: int) -> ExternalLink:
    link = link_crud.get(db, link_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        )
    return link


def _get_doc_or_404(db: Session, doc_id: int) -> RecruitmentDocument:
    doc = doc_crud.get(db, doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return doc


# ---- External Links ----


@router.get("/links", response_model=Page[LinkOut])
def list_links(
    page: Pagination = Depends(pagination),
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[LinkOut]:
    rows, total = link_crud.list(
        db,
        skip=page.skip,
        limit=page.limit,
        search=search,
        search_fields=_LINK_SEARCH_FIELDS,
        filters={"category": category, "is_active": is_active},
        order_by=ExternalLink.sort_order,
    )
    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.post("/links", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
def create_link(
    body: LinkCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExternalLink:
    # mode="json" serializes HttpUrl -> str so it fits the String column.
    return link_crud.create(db, body.model_dump(mode="json"))


@router.patch("/links/{link_id}", response_model=LinkOut)
def update_link(
    link_id: int,
    body: LinkUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExternalLink:
    link = _get_link_or_404(db, link_id)
    return link_crud.update(db, link, body.model_dump(exclude_unset=True, mode="json"))


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    link_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    link = _get_link_or_404(db, link_id)
    link_crud.delete(db, link)


# ---- Documents ----


@router.get("/documents", response_model=Page[DocumentOut])
def list_documents(
    page: Pagination = Depends(pagination),
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[DocumentOut]:
    rows, total = doc_crud.list(
        db,
        skip=page.skip,
        limit=page.limit,
        search=search,
        search_fields=_DOC_SEARCH_FIELDS,
        filters={"category": category, "is_active": is_active},
        order_by=RecruitmentDocument.sort_order,
    )
    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.post(
    "/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    title: str = "",
    description: str = "",
    category: str = "general",
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecruitmentDocument:
    # Read file bytes
    contents = await file.read()
    file_size = len(contents)

    # Enforce size limit
    if file_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size {file_size} bytes exceeds maximum "
                f"{settings.max_upload_bytes} bytes"
            ),
        )

    original_filename = file.filename or "unnamed"
    safe_filename = _secure_filename(original_filename)
    content_type = file.content_type or "application/octet-stream"

    # Use title if provided, otherwise derive from filename
    doc_title = title or Path(original_filename).stem

    # Documents are stored as bytea in Postgres. They rarely change and this keeps
    # them inside the nightly pg_dump backup — no external blob store.
    doc = doc_crud.create(
        db,
        {
            "title": doc_title,
            "description": description or None,
            "filename": safe_filename,
            "original_filename": original_filename,
            "file_size": file_size,
            "file_type": content_type,
            "category": category,
            "file_data": contents,
        },
    )
    return doc


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    doc = _get_doc_or_404(db, doc_id)

    # Documents are stored as bytea in Postgres.
    if doc.file_data:
        file_bytes = doc.file_data
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File data not found"
        )

    # Stream the file
    content_type = doc.file_type or "application/octet-stream"
    headers = {
        "Content-Disposition": f'attachment; filename="{doc.original_filename}"'
    }

    def iter_bytes():
        yield file_bytes

    return StreamingResponse(iter_bytes(), media_type=content_type, headers=headers)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    doc = _get_doc_or_404(db, doc_id)
    doc_crud.delete(db, doc)
