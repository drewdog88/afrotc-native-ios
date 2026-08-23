"""Transactional email via Resend. Plain-text only.

All sends are best-effort: failures are logged and swallowed so a public
submission is never turned into an error by a downstream email problem.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("afrotc695.email")

_RESEND_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False otherwise."""
    if not settings.resend_api_key or not settings.resend_from_email:
        logger.warning("Email not configured (resend_api_key/from unset); skipping send to %s.", to)
        return False
    if not to:
        return False
    try:
        resp = httpx.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.resend_from_email,
                "to": [to],
                "subject": subject,
                "text": body,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort; never propagate
        logger.error("Resend send to %s failed: %s", to, exc)
        return False


def render_ack(subject_template: str, body_template: str, first_name: str) -> tuple[str, str]:
    return (
        subject_template.replace("{{first_name}}", first_name),
        body_template.replace("{{first_name}}", first_name),
    )


def build_recruiter_notification(recruit) -> tuple[str, str]:
    """Subject/body for the internal 'new lead' notification."""
    subject = f"New AFROTC interest: {recruit.first_name} {recruit.last_name}"
    term_line = f"{recruit.intended_entry_term or '-'} {recruit.intended_entry_year or ''}".rstrip()
    lines = [
        "A new request-information form was submitted:",
        "",
        f"Name:    {recruit.first_name} {recruit.last_name}",
        f"Email:   {recruit.email or '-'}",
        f"Phone:   {recruit.phone or '-'}",
        f"School:  {recruit.current_school}",
        f"Grade:   {recruit.grade_level or '-'}",
        f"Term:    {term_line}",
        "",
        "Open the recruiting dashboard to view this lead.",
    ]
    return subject, "\n".join(lines)
