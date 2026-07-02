"""ORM models for the AFROTC 695 backend."""
from app.models.cadet import Cadet
from app.models.contact import RecruitmentEvent, UniversityContact
from app.models.content import ExternalLink, RecruitmentDocument
from app.models.enums import (
    CadetStatus,
    EventStatus,
    RecruitStage,
    SchoolType,
    UserRole,
)
from app.models.followup import FollowUp, FollowUpStatus
from app.models.recruit import PotentialRecruit, RecruitStageEvent
from app.models.user import ActivityLog, PasswordHistory, User

__all__ = [
    "ActivityLog",
    "Cadet",
    "CadetStatus",
    "EventStatus",
    "ExternalLink",
    "FollowUp",
    "FollowUpStatus",
    "PasswordHistory",
    "PotentialRecruit",
    "RecruitStage",
    "RecruitStageEvent",
    "RecruitmentDocument",
    "RecruitmentEvent",
    "SchoolType",
    "UniversityContact",
    "User",
    "UserRole",
]
