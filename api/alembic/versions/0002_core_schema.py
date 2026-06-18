"""core schema: trainers, clients, exercises, programs tree

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GLOBAL_EXERCISE_SEED = [
    "Back Squat",
    "Barbell Curl",
    "Barbell Row",
    "Bench Press",
    "Bulgarian Split Squat",
    "Cable Crunch",
    "Calf Raise",
    "Chin-Up",
    "Deadlift",
    "Dumbbell Bench Press",
    "Dumbbell Curl",
    "Dumbbell Row",
    "Dumbbell Shoulder Press",
    "Face Pull",
    "Front Squat",
    "Hanging Leg Raise",
    "Hip Thrust",
    "Incline Bench Press",
    "Lat Pulldown",
    "Lateral Raise",
    "Leg Curl",
    "Leg Extension",
    "Leg Press",
    "Overhead Press",
    "Plank",
    "Pull-Up",
    "Push-Up",
    "Romanian Deadlift",
    "Seated Cable Row",
    "Skullcrusher",
    "Triceps Pushdown",
    "Walking Lunge",
]


def upgrade() -> None:
    op.create_table(
        "trainers",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("business_name", sa.String(length=120), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("settings", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trainers")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_trainers_user_id_users"), ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", name=op.f("uq_trainers_user_id")),
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "invited",
                "active",
                "paused",
                name="client_status",
                native_enum=False,
                length=20,
                create_constraint=True,
            ),
            server_default="invited",
            nullable=False,
        ),
        sa.Column("invite_token_hash", sa.String(length=64), nullable=True),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
        sa.ForeignKeyConstraint(
            ["trainer_id"],
            ["trainers.id"],
            name=op.f("fk_clients_trainer_id_trainers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_clients_user_id_users"), ondelete="CASCADE"
        ),
        sa.UniqueConstraint("trainer_id", "email", name="uq_clients_trainer_id_email"),
        sa.UniqueConstraint("user_id", name=op.f("uq_clients_user_id")),
        sa.UniqueConstraint("invite_token_hash", name=op.f("uq_clients_invite_token_hash")),
    )
    op.create_index(op.f("ix_clients_trainer_id"), "clients", ["trainer_id"], unique=False)

    op.create_table(
        "exercises",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=True),
        sa.Column("parent_exercise_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
        sa.ForeignKeyConstraint(
            ["trainer_id"],
            ["trainers.id"],
            name=op.f("fk_exercises_trainer_id_trainers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_exercise_id"],
            ["exercises.id"],
            name=op.f("fk_exercises_parent_exercise_id_exercises"),
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("trainer_id", "name", name="uq_exercises_trainer_id_name"),
    )
    op.create_index(op.f("ix_exercises_trainer_id"), "exercises", ["trainer_id"], unique=False)

    op.create_table(
        "programs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_template", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("source_program_id", sa.Uuid(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_programs")),
        sa.ForeignKeyConstraint(
            ["trainer_id"],
            ["trainers.id"],
            name=op.f("fk_programs_trainer_id_trainers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_programs_client_id_clients"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_program_id"],
            ["programs.id"],
            name=op.f("fk_programs_source_program_id_programs"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(op.f("ix_programs_trainer_id"), "programs", ["trainer_id"], unique=False)
    op.create_index(op.f("ix_programs_client_id"), "programs", ["client_id"], unique=False)

    op.create_table(
        "program_blocks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_program_blocks")),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_program_blocks_program_id_programs"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_program_blocks_program_id"), "program_blocks", ["program_id"], unique=False
    )

    op.create_table(
        "program_weeks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("block_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_program_weeks")),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["program_blocks.id"],
            name=op.f("fk_program_weeks_block_id_program_blocks"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("ix_program_weeks_block_id"), "program_weeks", ["block_id"], unique=False)

    op.create_table(
        "program_days",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("week_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("is_rest_day", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_program_days")),
        sa.ForeignKeyConstraint(
            ["week_id"],
            ["program_weeks.id"],
            name=op.f("fk_program_days_week_id_program_weeks"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("ix_program_days_week_id"), "program_days", ["week_id"], unique=False)

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("day_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("rep_scheme", JSONB(), nullable=False),
        sa.Column("load_scheme", JSONB(), nullable=True),
        sa.Column("tempo", sa.String(length=20), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prescriptions")),
        sa.ForeignKeyConstraint(
            ["day_id"],
            ["program_days.id"],
            name=op.f("fk_prescriptions_day_id_program_days"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_prescriptions_exercise_id_exercises"),
            ondelete="RESTRICT",
        ),
    )
    op.create_index(op.f("ix_prescriptions_day_id"), "prescriptions", ["day_id"], unique=False)
    op.create_index(
        op.f("ix_prescriptions_exercise_id"), "prescriptions", ["exercise_id"], unique=False
    )

    # Seed the shared global exercise library (trainer_id NULL).
    exercises = sa.table("exercises", sa.column("name", sa.String))
    op.bulk_insert(exercises, [{"name": name} for name in GLOBAL_EXERCISE_SEED])


def downgrade() -> None:
    op.drop_table("prescriptions")
    op.drop_table("program_days")
    op.drop_table("program_weeks")
    op.drop_table("program_blocks")
    op.drop_table("programs")
    op.drop_table("exercises")
    op.drop_table("clients")
    op.drop_table("trainers")
