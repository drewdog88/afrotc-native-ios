"""Aggregate every /api/v1 router into one APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    analytics,
    auth,
    cadets,
    contacts,
    events,
    exports,
    followups,
    imports,
    materials,
    profile,
    recruits,
)

api_router = APIRouter()
# Auth + core entities.
api_router.include_router(auth.router)
api_router.include_router(recruits.router)
api_router.include_router(cadets.router)
api_router.include_router(contacts.router)
api_router.include_router(events.router)
api_router.include_router(followups.router)
api_router.include_router(materials.router)
# Analytics / dashboard (the recruitment-change-over-time reporting).
api_router.include_router(analytics.router)
# Bulk import + exports.
api_router.include_router(imports.router)
api_router.include_router(exports.router)
# Self-service profile + 2FA, and admin.
api_router.include_router(profile.router)
api_router.include_router(admin.router)
