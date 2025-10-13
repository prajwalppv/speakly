"""Initial schema for Speakly on Postgres.

Revision ID: 001
Revises: 
Create Date: 2025-02-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE TYPE speakersegment_source AS ENUM ('manual', 'auto')"))
    op.execute(sa.text("CREATE TYPE llmrun_status AS ENUM ('pending', 'in_progress', 'completed', 'failed')"))
    op.execute(sa.text("CREATE TYPE todo_status AS ENUM ('pending', 'in_progress', 'completed', 'blocked')"))

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("clerk_user_id", sa.String(), nullable=True),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("clerk_user_id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"])

    op.create_table(
        "speaker_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("embedding_path", sa.String(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("external_id"),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("auto_generated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tags_id", "tags", ["id"])
    op.create_index("ix_tags_name", "tags", ["name"])

    op.create_table(
        "ticktick_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("refresh_token", sa.String(), nullable=True),
        sa.Column("token_type", sa.String(), nullable=False, server_default="bearer"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False, server_default="tasks:write tasks:read"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("audio_path", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_transcribed_at", sa.DateTime(), nullable=True),
        sa.Column("has_pj", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("summary_run_id", sa.Integer(), nullable=True),
        sa.Column("todo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_stages", sa.JSON(), nullable=True),
    )
    op.create_index("ix_sessions_id", "sessions", ["id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "transcriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="elevenlabs"),
        sa.Column("provider_job_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("channel_count", sa.Integer(), nullable=True),
    )
    op.create_index("ix_transcriptions_id", "transcriptions", ["id"])
    op.create_index("ix_transcriptions_session_id", "transcriptions", ["session_id"])
    op.create_index("ix_transcriptions_provider_job_id", "transcriptions", ["provider_job_id"])

    op.create_table(
        "transcription_edits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transcription_id", sa.Integer(), sa.ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("previous_text", sa.Text(), nullable=False),
        sa.Column("new_text", sa.Text(), nullable=False),
        sa.Column("edit_type", sa.String(), nullable=False, server_default="manual"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_transcription_edits_id", "transcription_edits", ["id"])
    op.create_index("ix_transcription_edits_transcription_id", "transcription_edits", ["transcription_id"])

    op.create_table(
        "llm_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transcription_id", sa.Integer(), sa.ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("run_type", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=True),
    )
    op.create_index("ix_llm_runs_session_id", "llm_runs", ["session_id"])
    op.create_index("ix_llm_runs_transcription_id", "llm_runs", ["transcription_id"])

    op.create_table(
        "speaker_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transcription_id", sa.Integer(), sa.ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("speaker_label", sa.String(), nullable=True),
        sa.Column("speaker_profile_id", sa.Integer(), sa.ForeignKey("speaker_profiles.id"), nullable=True),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_pj", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("channel_index", sa.Integer(), nullable=True),
        sa.Column("attributes_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_speaker_segments_session_id", "speaker_segments", ["session_id"])
    op.create_index("ix_speaker_segments_transcription_id", "speaker_segments", ["transcription_id"])

    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("llm_run_id", sa.Integer(), sa.ForeignKey("llm_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("due_hint", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("source_start_ms", sa.Integer(), nullable=True),
        sa.Column("source_end_ms", sa.Integer(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("ticktick_task_id", sa.String(), nullable=True),
        sa.Column("ticktick_project_id", sa.String(), nullable=True),
        sa.Column("ticktick_synced_at", sa.DateTime(), nullable=True),
        sa.Column("ticktick_sync_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("ticktick_sync_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_todos_session_id", "todos", ["session_id"])
    op.create_index("ix_todos_llm_run_id", "todos", ["llm_run_id"])
    op.create_index("ix_todos_ticktick_task_id", "todos", ["ticktick_task_id"])

    op.create_table(
        "session_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("auto_generated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_session_tags_session_id", "session_tags", ["session_id"])
    op.create_index("ix_session_tags_tag_id", "session_tags", ["tag_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("preference_id", sa.Integer(), nullable=True),
        sa.Column("cadence", sa.String(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_period_start", "reports", ["period_start"])

    op.create_table(
        "report_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cadence", sa.String(), nullable=False, server_default="weekly"),
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("delivery_channels", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("next_scheduled_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_report_preferences_user_id", "report_preferences", ["user_id"])


def downgrade() -> None:
    op.drop_table("report_preferences")
    op.drop_index("ix_reports_period_start", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_session_tags_tag_id", table_name="session_tags")
    op.drop_index("ix_session_tags_session_id", table_name="session_tags")
    op.drop_table("session_tags")
    op.drop_index("ix_todos_ticktick_task_id", table_name="todos")
    op.drop_index("ix_todos_llm_run_id", table_name="todos")
    op.drop_index("ix_todos_session_id", table_name="todos")
    op.drop_table("todos")
    op.drop_index("ix_speaker_segments_transcription_id", table_name="speaker_segments")
    op.drop_index("ix_speaker_segments_session_id", table_name="speaker_segments")
    op.drop_table("speaker_segments")
    op.drop_index("ix_llm_runs_transcription_id", table_name="llm_runs")
    op.drop_index("ix_llm_runs_session_id", table_name="llm_runs")
    op.drop_table("llm_runs")
    op.drop_index("ix_transcription_edits_transcription_id", table_name="transcription_edits")
    op.drop_index("ix_transcription_edits_id", table_name="transcription_edits")
    op.drop_table("transcription_edits")
    op.drop_index("ix_transcriptions_provider_job_id", table_name="transcriptions")
    op.drop_index("ix_transcriptions_session_id", table_name="transcriptions")
    op.drop_index("ix_transcriptions_id", table_name="transcriptions")
    op.drop_table("transcriptions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("ticktick_tokens")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_index("ix_tags_id", table_name="tags")
    op.drop_table("tags")
    op.drop_table("speaker_profiles")
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
    op.execute(sa.text("DROP TYPE todo_status"))
    op.execute(sa.text("DROP TYPE llmrun_status"))
    op.execute(sa.text("DROP TYPE speakersegment_source"))
