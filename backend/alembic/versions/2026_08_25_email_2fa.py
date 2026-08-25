"""email 2FA + trusted devices

Additive: new nullable/defaulted columns on users + a trusted_devices table.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers.
revision = "email2fa0001"
down_revision = "6bff7689c532"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("two_factor_method", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("two_factor_enrollment_prompted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("otp_code_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("otp_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("otp_resends", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("otp_purpose", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("otp_last_sent_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "trusted_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("device_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("trusted_devices")
    for col in (
        "otp_last_sent_at", "otp_purpose", "otp_resends", "otp_attempts",
        "otp_expires_at", "otp_code_hash", "two_factor_enrollment_prompted",
        "two_factor_enabled", "two_factor_method",
    ):
        op.drop_column("users", col)
