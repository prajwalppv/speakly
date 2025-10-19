"""Set manual review as default recording preference.

Revision ID: 007
Revises: 006
Create Date: 2025-02-17 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression


revision = "007"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "auto_approve_sessions",
        server_default=expression.false(),
    )
    op.execute(sa.text("UPDATE users SET auto_approve_sessions = false"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE users SET auto_approve_sessions = true"))
    op.alter_column(
        "users",
        "auto_approve_sessions",
        server_default=expression.true(),
    )
