"""Admin intake-settings endpoints + bootstrap seed."""
from __future__ import annotations

from app.bootstrap import bootstrap_intake_settings
from app.models import IntakeSettings
from tests.conftest import TestingSessionLocal


def test_bootstrap_seeds_single_settings_row() -> None:
    with TestingSessionLocal() as db:
        bootstrap_intake_settings(db)
        bootstrap_intake_settings(db)  # idempotent — second call is a no-op
        rows = db.query(IntakeSettings).all()
        assert len(rows) == 1
        assert rows[0].id == 1
        assert rows[0].ack_email_subject  # default is non-empty
