"""activity_log user_id nullable for public actions

Revision ID: 6bff7689c532
Revises: b7d9cab9c8bb
Create Date: 2026-08-23 17:09:06.078807
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bff7689c532'
down_revision: str | None = 'b7d9cab9c8bb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Public/system actions (e.g. a public request-info submission) have no
    # signed-in user, so activity_log.user_id must allow NULL.
    with op.batch_alter_table("activity_log", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id", existing_type=sa.Integer(), nullable=True
        )


def downgrade() -> None:
    with op.batch_alter_table("activity_log", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id", existing_type=sa.Integer(), nullable=False
        )
