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
    OTHER = "other"  # GED / community college / non-standard path


class GradeLevel(StrEnum):
    HS_9 = "hs_9"
    HS_10 = "hs_10"
    HS_11 = "hs_11"
    HS_12 = "hs_12"
    COLLEGE_FRESHMAN = "college_freshman"
    COLLEGE_SOPHOMORE = "college_sophomore"
    COLLEGE_JUNIOR = "college_junior"
    COLLEGE_SENIOR = "college_senior"
    OTHER = "other"


class IntendedTerm(StrEnum):
    FALL = "fall"
    SPRING = "spring"


# Maps a submitted grade level to the school_type stored on the recruit.
# OTHER stays OTHER (never silently labeled college).
def school_type_for_grade(grade: GradeLevel) -> SchoolType:
    if grade in (GradeLevel.HS_9, GradeLevel.HS_10, GradeLevel.HS_11, GradeLevel.HS_12):
        return SchoolType.HIGH_SCHOOL
    if grade == GradeLevel.OTHER:
        return SchoolType.OTHER
    return SchoolType.COLLEGE


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
