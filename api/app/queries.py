"""Shared query fragments."""

from sqlalchemy.orm import selectinload

from app.models.program import Program, ProgramBlock, ProgramDay, ProgramWeek

PROGRAM_FULL_TREE = (
    selectinload(Program.blocks)
    .selectinload(ProgramBlock.weeks)
    .selectinload(ProgramWeek.days)
    .selectinload(ProgramDay.prescriptions),
)
