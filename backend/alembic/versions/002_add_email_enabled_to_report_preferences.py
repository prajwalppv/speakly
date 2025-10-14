"""add email_enabled to report preferences

Revision ID: 002
Revises: 001
Create Date: 2025-02-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_preferences",
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("report_preferences", "email_enabled")
