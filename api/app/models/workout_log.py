import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WorkoutLog(Base):
    """A logged workout session. Offline-sync friendly: ids are generated on
    the client and writes are idempotent upserts (POST /me/sync)."""

    __tablename__ = "workout_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Soft link to the prescribed day; survives program edits via SET NULL.
    program_day_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("program_days.id", ondelete="SET NULL")
    )
    workout_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    set_logs: Mapped[list["SetLog"]] = relationship(
        back_populates="workout_log",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SetLog.position",
    )


class SetLog(Base):
    """One performed set: actuals vs prescribed. exercise_name and
    prescribed_snapshot are denormalized at log time so history stays readable
    even if the program or a custom exercise is later edited/deleted."""

    __tablename__ = "set_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    workout_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prescription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="SET NULL")
    )
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="SET NULL"), index=True
    )
    exercise_name: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float | None] = mapped_column(Float)
    weight_unit: Mapped[str | None] = mapped_column(String(2))
    reps: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    rpe: Mapped[float | None] = mapped_column(Float)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    prescribed_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    workout_log: Mapped[WorkoutLog] = relationship(back_populates="set_logs")
