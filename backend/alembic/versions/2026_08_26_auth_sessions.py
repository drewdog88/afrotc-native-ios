"""auth sessions

Additive: a new auth_sessions table backing the sid claim in access/refresh tokens.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "authsess0001"
down_revision = "email2fa0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("sid", sa.String(length=36), nullable=False),
        sa.Column("device_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_sessions_sid", "auth_sessions", ["sid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_sid", table_name="auth_sessions")
    op.drop_table("auth_sessions")
