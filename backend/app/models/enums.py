"""Enumerations used across the domain model.

Stored as plain strings in the DB (via native str values) so migrating existing
free-text values and generating OpenAPI/Swift enums stays simple.
"""
from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    RECRUITER = "recruiter"
    VIEWER = "viewer"  # read-only: sees everything, cannot create/edit/delete


class SchoolType(StrEnum):
    HIGH_SCHOOL = "high_school"
    COLLEGE = "college"


class RecruitStage(StrEnum):
    """The recruitment funnel. Ordered from first contact to commissioning.

    Stage transitions are recorded in RecruitStageEvent, which powers the
    funnel + trend-over-time analytics.
    """

    LEAD = "lead"
    CONTACTED = "contacted"
    APPLIED = "applied"
    ENROLLED = "enrolled"
    COMMISSIONED = "commissioned"
    DECLINED = "declined"


# Canonical funnel order (DECLINED is terminal/off-funnel, excluded from the
# conversion ladder but still reportable).
FUNNEL_ORDER: list[RecruitStage] = [
    RecruitStage.LEAD,
    RecruitStage.CONTACTED,
    RecruitStage.APPLIED,
    RecruitStage.ENROLLED,
    RecruitStage.COMMISSIONED,
]


class CadetStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"


class EventStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
