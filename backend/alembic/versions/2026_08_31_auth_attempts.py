"""auth attempts

Additive: a new auth_attempts table backing the per-IP throttle on the
unauthenticated auth endpoints (login / reset-password / forgot-password).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "authattempt01"
down_revision = "authsess0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("endpoint", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_attempts_ip_address", "auth_attempts", ["ip_address"])
    op.create_index("ix_auth_attempts_created_at", "auth_attempts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_attempts_created_at", table_name="auth_attempts")
    op.drop_index("ix_auth_attempts_ip_address", table_name="auth_attempts")
    op.drop_table("auth_attempts")
