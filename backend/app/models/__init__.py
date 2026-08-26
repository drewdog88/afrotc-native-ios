"""ORM models for the AFROTC 695 backend."""
from app.models.auth_session import AuthSession
from app.models.cadet import Cadet
from app.models.contact import RecruitmentEvent, UniversityContact
from app.models.content import ExternalLink, RecruitmentDocument
from app.models.enums import (
    CadetStatus,
    EventStatus,
    GradeLevel,
    IntendedTerm,
    RecruitStage,
    SchoolType,
    UserRole,
)
from app.models.followup import FollowUp, FollowUpStatus
from app.models.recruit import PotentialRecruit, RecruitStageEvent
from app.models.settings import IntakeSettings
from app.models.trusted_device import TrustedDevice
from app.models.user import ActivityLog, PasswordHistory, User

__all__ = [
    "ActivityLog",
    "AuthSession",
    "Cadet",
    "CadetStatus",
    "EventStatus",
    "ExternalLink",
    "FollowUp",
    "FollowUpStatus",
    "GradeLevel",
    "IntakeSettings",
    "IntendedTerm",
    "PasswordHistory",
    "PotentialRecruit",
    "RecruitStage",
    "RecruitStageEvent",
    "RecruitmentDocument",
    "RecruitmentEvent",
    "SchoolType",
    "TrustedDevice",
    "UniversityContact",
    "User",
    "UserRole",
]
