"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("afrotc695")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned exclusively by Alembic migrations (see alembic/); the app
    # never creates tables itself. There is no local/SQLite fallback.
    from app.bootstrap import bootstrap_admin

    with SessionLocal() as db:
        bootstrap_admin(db)

    yield


app = FastAPI(
    title="AFROTC Det 695 Recruitment API",
    version="0.1.0",
    description="Headless API powering the Det 695 web and iOS recruitment apps.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": "AFROTC Det 695 Recruitment API", "docs": "/docs"}
