"""intake form: recruit columns + intake_settings

Revision ID: b7d9cab9c8bb
Revises: 2082358eabfe
Create Date: 2026-08-23 10:54:12.806852
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7d9cab9c8bb'
down_revision: str | None = '2082358eabfe'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intake_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recruiter_notification_email", sa.String(length=120), nullable=True),
        sa.Column("ack_email_subject", sa.String(length=200), nullable=False),
        sa.Column("ack_email_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("potential_recruit", schema=None) as batch_op:
        batch_op.add_column(sa.Column("grade_level", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("intended_entry_term", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("intended_entry_year", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("acknowledgment_email_sent_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("source", sa.String(length=20), server_default="manual", nullable=False)
        )
        batch_op.add_column(sa.Column("source_ip", sa.String(length=45), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("potential_recruit", schema=None) as batch_op:
        batch_op.drop_column("source_ip")
        batch_op.drop_column("source")
        batch_op.drop_column("acknowledgment_email_sent_at")
        batch_op.drop_column("consent_given_at")
        batch_op.drop_column("intended_entry_year")
        batch_op.drop_column("intended_entry_term")
        batch_op.drop_column("grade_level")
    op.drop_table("intake_settings")
