import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Sync contract: the mobile app generates UUIDs locally and pushes batches.
# Upserts are idempotent by id; per-item results let one bad record fail
# without blocking the rest of the queue.


class SetLogIn(BaseModel):
    id: uuid.UUID
    prescription_id: uuid.UUID | None = None
    exercise_id: uuid.UUID | None = None
    exercise_name: str = Field(min_length=1, max_length=160)
    position: int = Field(ge=0, le=1000)
    set_number: int = Field(ge=1, le=100)
    weight: float | None = Field(default=None, ge=0, le=2000)
    weight_unit: Literal["kg", "lb"] | None = None
    reps: int | None = Field(default=None, ge=0, le=500)
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    rpe: float | None = Field(default=None, ge=1, le=10)
    is_completed: bool = True
    prescribed_snapshot: dict | None = None


class WorkoutLogIn(BaseModel):
    id: uuid.UUID
    program_day_id: uuid.UUID | None = None
    workout_date: date
    notes: str | None = Field(default=None, max_length=10_000)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    set_logs: list[SetLogIn] = Field(default_factory=list, max_length=300)


class SyncRequest(BaseModel):
    workout_logs: list[WorkoutLogIn] = Field(max_length=100)


class SyncResultItem(BaseModel):
    id: uuid.UUID
    status: Literal["created", "updated", "rejected"]
    detail: str | None = None


class SyncResponse(BaseModel):
    results: list[SyncResultItem]


class SetLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prescription_id: uuid.UUID | None
    exercise_id: uuid.UUID | None
    exercise_name: str
    position: int
    set_number: int
    weight: float | None
    weight_unit: str | None
    reps: int | None
    duration_seconds: int | None
    rpe: float | None
    is_completed: bool
    prescribed_snapshot: dict | None


class WorkoutLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    program_day_id: uuid.UUID | None
    workout_date: date
    notes: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    set_logs: list[SetLogOut]
