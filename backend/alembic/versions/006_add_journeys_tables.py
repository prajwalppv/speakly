"""add report preferences and reports tables

Revision ID: 006
Revises: 005
Create Date: 2025-02-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


report_cadence_enum = sa.Enum(
    "daily",
    "weekly",
    "biweekly",
    "monthly",
    "quarterly",
    "yearly",
    name="report_cadence",
    native_enum=False,
)

report_status_enum = sa.Enum(
    "pending",
    "in_progress",
    "completed",
    "failed",
    name="report_status",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    report_cadence_enum.create(bind, checkfirst=True)
    report_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "report_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "cadence",
            report_cadence_enum,
            nullable=False,
            server_default="weekly",
        ),
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("delivery_channels", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("next_scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_report_preferences_user_id"),
    )
    op.create_index(op.f("ix_report_preferences_user_id"), "report_preferences", ["user_id"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("preference_id", sa.Integer(), nullable=True),
        sa.Column(
            "cadence",
            report_cadence_enum,
            nullable=False,
            server_default="weekly",
        ),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            report_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["preference_id"], ["report_preferences.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_user_id"), "reports", ["user_id"], unique=False)
    op.create_index(op.f("ix_reports_preference_id"), "reports", ["preference_id"], unique=False)
    op.create_index(op.f("ix_reports_period_start"), "reports", ["period_start"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_period_start"), table_name="reports")
    op.drop_index(op.f("ix_reports_preference_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_user_id"), table_name="reports")
    op.drop_table("reports")

    op.drop_index(op.f("ix_report_preferences_user_id"), table_name="report_preferences")
    op.drop_table("report_preferences")

    bind = op.get_bind()
    report_status_enum.drop(bind, checkfirst=True)
    report_cadence_enum.drop(bind, checkfirst=True)
