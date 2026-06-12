import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.scheme import LoadScheme, RepScheme

# --- structure input (PUT /programs/{id}/structure) ---
# Children carry an optional id: present = update that row (must already belong
# to the same parent), absent = create. Existing rows not referenced are
# deleted. Order in each list defines position — preserving ids keeps future
# workout logs (Phase 2) pointing at stable prescriptions.


class PrescriptionIn(BaseModel):
    id: uuid.UUID | None = None
    exercise_id: uuid.UUID
    sets: int = Field(ge=1, le=100)
    rep_scheme: RepScheme
    load_scheme: LoadScheme | None = None
    tempo: str | None = Field(default=None, max_length=20)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    notes: str | None = None


class DayIn(BaseModel):
    id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=160)
    is_rest_day: bool = False
    notes: str | None = None
    prescriptions: list[PrescriptionIn] = []


class WeekIn(BaseModel):
    id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=160)
    days: list[DayIn] = []


class BlockIn(BaseModel):
    id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    notes: str | None = None
    weeks: list[WeekIn] = []


class ProgramStructureIn(BaseModel):
    blocks: list[BlockIn] = []


# --- program CRUD ---


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    client_id: uuid.UUID | None = None
    is_template: bool = False
    starts_on: date | None = None


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    client_id: uuid.UUID | None = None  # explicit null unassigns (exclude_unset semantics)
    is_template: bool | None = None
    starts_on: date | None = None


class ProgramDuplicate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    as_template: bool = False
    client_id: uuid.UUID | None = None


# --- output ---


class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_id: uuid.UUID
    position: int
    sets: int
    rep_scheme: RepScheme
    load_scheme: LoadScheme | None
    tempo: str | None
    rest_seconds: int | None
    notes: str | None


class DayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    is_rest_day: bool
    notes: str | None
    position: int
    prescriptions: list[PrescriptionOut]


class WeekOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    position: int
    days: list[DayOut]


class BlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    notes: str | None
    position: int
    weeks: list[WeekOut]


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    client_id: uuid.UUID | None
    is_template: bool
    version: int
    source_program_id: uuid.UUID | None
    starts_on: date | None
    created_at: datetime
    updated_at: datetime


class ProgramDetailOut(ProgramOut):
    blocks: list[BlockOut]
