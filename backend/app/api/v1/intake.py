"""Public, UNAUTHENTICATED request-info intake.

Creates a PotentialRecruit lead (stage=LEAD, source=public_intake_form), then
best-effort emails the recruiter and the applicant. The DB commit is the source
of truth; email/Turnstile-adjacent failures never fail an accepted submission.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import now_utc
from app.models import IntakeSettings, PotentialRecruit, RecruitStageEvent
from app.models.enums import GradeLevel, IntendedTerm, RecruitStage, school_type_for_grade
from app.models.settings import DEFAULT_ACK_BODY, DEFAULT_ACK_SUBJECT
from app.schemas.intake import IntakeCreate, IntakeOptions, IntakeSubmitResult, _Option
from app.services.activity import record_activity
from app.services.email import build_recruiter_notification, render_ack, send_email
from app.services.spam import client_ip, too_many_from_ip, verify_turnstile

logger = logging.getLogger("afrotc695.intake")

router = APIRouter(prefix="/intake", tags=["intake"])

_GRADE_LABELS = {
    GradeLevel.HS_9: "9th grade", GradeLevel.HS_10: "10th grade",
    GradeLevel.HS_11: "11th grade", GradeLevel.HS_12: "12th grade",
    GradeLevel.COLLEGE_FRESHMAN: "College freshman",
    GradeLevel.COLLEGE_SOPHOMORE: "College sophomore",
    GradeLevel.COLLEGE_JUNIOR: "College junior",
    GradeLevel.COLLEGE_SENIOR: "College senior",
    GradeLevel.OTHER: "Other",
}
_TERM_LABELS = {IntendedTerm.FALL: "Fall", IntendedTerm.SPRING: "Spring"}


@router.get("/options", response_model=IntakeOptions)
def intake_options() -> IntakeOptions:
    return IntakeOptions(
        grade_levels=[_Option(value=g.value, label=_GRADE_LABELS[g]) for g in GradeLevel],
        terms=[_Option(value=t.value, label=_TERM_LABELS[t]) for t in IntendedTerm],
    )


@router.post("", response_model=IntakeSubmitResult, status_code=status.HTTP_201_CREATED)
def submit_intake(
    body: IntakeCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> IntakeSubmitResult:
    ip = client_ip(request)

    if not verify_turnstile(body.turnstile_token, ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed. Please try again.",
        )
    if too_many_from_ip(db, ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Please try again later.",
        )

    recruit = PotentialRecruit(
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        email=str(body.email),
        phone=body.phone.strip(),
        current_school=body.current_school.strip(),
        grade_level=body.grade_level.value,
        school_type=school_type_for_grade(body.grade_level).value,
        intended_entry_term=body.intended_entry_term.value,
        intended_entry_year=body.intended_entry_year,
        stage=RecruitStage.LEAD.value,
        source="public_intake_form",
        source_ip=ip,
        consent_given_at=now_utc(),
    )
    db.add(recruit)
    db.flush()  # assign recruit.id
    db.add(RecruitStageEvent(
        recruit_id=recruit.id, from_stage=None, to_stage=recruit.stage,
        changed_by_id=None, note="Submitted public request-info form",
    ))
    db.commit()
    db.refresh(recruit)

    # --- Best-effort notifications (never fail the accepted submission) ---
    settings_row = db.get(IntakeSettings, 1)
    recruiter_email = settings_row.recruiter_notification_email if settings_row else None
    recruiter_status = "not configured"
    if recruiter_email:
        subject, notif_body = build_recruiter_notification(recruit)
        recruiter_status = "sent" if send_email(recruiter_email, subject, notif_body) else "failed"

    # Always attempt the applicant acknowledgment, falling back to the packaged
    # defaults if the settings row is missing (defense in depth — bootstrap seeds it,
    # but a missing row must never silently drop a candidate's acknowledgment).
    ack_subject_tmpl = settings_row.ack_email_subject if settings_row else DEFAULT_ACK_SUBJECT
    ack_body_tmpl = settings_row.ack_email_body if settings_row else DEFAULT_ACK_BODY
    subj, body_text = render_ack(ack_subject_tmpl, ack_body_tmpl, recruit.first_name)
    ack_sent = send_email(recruit.email, subj, body_text)
    if ack_sent:
        try:
            recruit.acknowledgment_email_sent_at = now_utc()
            db.commit()
        except Exception:
            # The lead is already durably saved (commit above). Failing to persist
            # this best-effort ack timestamp must never fail the accepted submission.
            db.rollback()
            logger.warning(
                "Failed to record acknowledgment_email_sent_at for recruit %s",
                recruit.id, exc_info=True,
            )

    # Audit trail: surface the public submission (and both email outcomes) in the
    # admin Activity Log. Best-effort — record_activity never raises.
    record_activity(
        db,
        username="Public form",
        action="CONTACT_SUBMITTED",
        table_name="potential_recruit",
        record_id=recruit.id,
        record_description=f"{recruit.first_name} {recruit.last_name}",
        details=(
            f"recruiter notification: {recruiter_status}; "
            f"acknowledgment: {'sent' if ack_sent else 'failed'}"
        ),
        request=request,
    )

    return IntakeSubmitResult()
