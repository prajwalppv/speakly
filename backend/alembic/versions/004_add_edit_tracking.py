"""add edit tracking and processing stages

Revision ID: 004
Revises: 003
Create Date: 2025-09-30 21:50:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add processing_stages to sessions table
    op.add_column('sessions', sa.Column('processing_stages', sa.JSON(), nullable=True))
    
    # Create transcription_edits table
    op.create_table(
        'transcription_edits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transcription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('previous_text', sa.Text(), nullable=False),
        sa.Column('new_text', sa.Text(), nullable=False),
        sa.Column('edit_type', sa.String(), nullable=False, server_default='manual'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['transcription_id'], ['transcriptions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcription_edits_transcription_id'), 'transcription_edits', ['transcription_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transcription_edits_transcription_id'), table_name='transcription_edits')
    op.drop_table('transcription_edits')
    op.drop_column('sessions', 'processing_stages')
