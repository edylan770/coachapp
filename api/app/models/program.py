import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
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


class Program(Base):
    """A training program: blocks → weeks → days → prescriptions.

    Versioning model (v1): editing happens in place; `duplicate` creates a new
    program with version = source.version + 1 and source_program_id set, which
    is the lineage AI program adjustments will build on in Phase 4."""

    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    trainer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_template: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    source_program_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("programs.id", ondelete="SET NULL")
    )
    # Anchor for mapping calendar dates to program days (used by the client
    # app's "today's workout" in Phase 2).
    starts_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    blocks: Mapped[list["ProgramBlock"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProgramBlock.position",
    )


class ProgramBlock(Base):
    __tablename__ = "program_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    program: Mapped[Program] = relationship(back_populates="blocks")
    weeks: Mapped[list["ProgramWeek"]] = relationship(
        back_populates="block",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProgramWeek.position",
    )


class ProgramWeek(Base):
    __tablename__ = "program_weeks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("program_blocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(160))
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    block: Mapped[ProgramBlock] = relationship(back_populates="weeks")
    days: Mapped[list["ProgramDay"]] = relationship(
        back_populates="week",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProgramDay.position",
    )


class ProgramDay(Base):
    __tablename__ = "program_days"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("program_weeks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(160))
    is_rest_day: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    notes: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    week: Mapped[ProgramWeek] = relationship(back_populates="days")
    prescriptions: Mapped[list["Prescription"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Prescription.position",
    )


class Prescription(Base):
    """One exercise prescription within a day. rep_scheme/load_scheme are JSONB
    validated by the Pydantic discriminated unions in app.schemas.scheme."""

    __tablename__ = "prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("program_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # RESTRICT: an exercise that is prescribed anywhere cannot be deleted.
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    rep_scheme: Mapped[dict] = mapped_column(JSONB, nullable=False)
    load_scheme: Mapped[dict | None] = mapped_column(JSONB)
    tempo: Mapped[str | None] = mapped_column(String(20))
    rest_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    day: Mapped[ProgramDay] = relationship(back_populates="prescriptions")
