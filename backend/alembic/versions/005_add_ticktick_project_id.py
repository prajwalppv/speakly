"""add ticktick project id

Revision ID: 005
Revises: 004
Create Date: 2025-10-01 11:32:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ticktick_project_id column to todos table
    op.add_column('todos', sa.Column('ticktick_project_id', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove ticktick_project_id column
    op.drop_column('todos', 'ticktick_project_id')
