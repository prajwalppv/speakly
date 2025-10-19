"""Add session review fields and user auto-approve preference.

Revision ID: 003
Revises: 002
Create Date: 2025-02-17 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auto_approve_sessions",
            sa.Boolean(),
            nullable=False,
            server_default=expression.true(),
        ),
    )

    op.add_column(
        "sessions",
        sa.Column(
            "review_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "reviewed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    # Ensure existing rows have proper defaults without relying on server defaults afterwards
    op.execute(sa.text("UPDATE users SET auto_approve_sessions = true WHERE auto_approve_sessions IS NULL"))
    op.execute(sa.text("UPDATE sessions SET review_status = 'pending' WHERE review_status IS NULL"))

    # Drop server default after data backfill to avoid locking in database-level default semantics
    op.alter_column("users", "auto_approve_sessions", server_default=None)
    op.alter_column("sessions", "review_status", server_default=None)


def downgrade() -> None:
    op.drop_column("sessions", "reviewed_at")
    op.drop_column("sessions", "review_status")
    op.drop_column("users", "auto_approve_sessions")
