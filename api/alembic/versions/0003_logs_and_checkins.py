"""workout logs, set logs, check-ins, client check-in cadence

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-12

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column(
            "checkin_cadence_days", sa.Integer(), server_default=sa.text("7"), nullable=False
        ),
    )

    op.create_table(
        "workout_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("program_day_id", sa.Uuid(), nullable=True),
        sa.Column("workout_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout_logs")),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_workout_logs_client_id_clients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_day_id"],
            ["program_days.id"],
            name=op.f("fk_workout_logs_program_day_id_program_days"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(op.f("ix_workout_logs_client_id"), "workout_logs", ["client_id"], unique=False)
    op.create_index(
        "ix_workout_logs_client_id_workout_date",
        "workout_logs",
        ["client_id", "workout_date"],
        unique=False,
    )

    op.create_table(
        "set_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workout_log_id", sa.Uuid(), nullable=False),
        sa.Column("prescription_id", sa.Uuid(), nullable=True),
        sa.Column("exercise_id", sa.Uuid(), nullable=True),
        sa.Column("exercise_name", sa.String(length=160), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("weight_unit", sa.String(length=2), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("rpe", sa.Float(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("prescribed_snapshot", JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_set_logs")),
        sa.ForeignKeyConstraint(
            ["workout_log_id"],
            ["workout_logs.id"],
            name=op.f("fk_set_logs_workout_log_id_workout_logs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prescription_id"],
            ["prescriptions.id"],
            name=op.f("fk_set_logs_prescription_id_prescriptions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_set_logs_exercise_id_exercises"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_set_logs_workout_log_id"), "set_logs", ["workout_log_id"], unique=False
    )
    op.create_index(op.f("ix_set_logs_exercise_id"), "set_logs", ["exercise_id"], unique=False)

    op.create_table(
        "check_ins",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("weight_unit", sa.String(length=2), nullable=True),
        sa.Column("measurements", JSONB(), nullable=True),
        sa.Column("photos", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("adherence", JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_check_ins")),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_check_ins_client_id_clients"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "client_id", "check_in_date", name="uq_check_ins_client_id_check_in_date"
        ),
    )
    op.create_index(op.f("ix_check_ins_client_id"), "check_ins", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_table("check_ins")
    op.drop_table("set_logs")
    op.drop_table("workout_logs")
    op.drop_column("clients", "checkin_cadence_days")
