import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.program import ProgramDetailOut


class Adherence(BaseModel):
    training: int | None = Field(default=None, ge=1, le=5)
    nutrition: int | None = Field(default=None, ge=1, le=5)
    sleep: int | None = Field(default=None, ge=1, le=5)


class CheckInCreate(BaseModel):
    # Optional client-generated id makes retries over flaky connections
    # idempotent (resubmitting the same id returns the stored check-in).
    id: uuid.UUID | None = None
    check_in_date: date
    weight: float | None = Field(default=None, gt=0, le=1500)
    weight_unit: Literal["kg", "lb"] = "kg"
    measurements: dict[str, float] | None = None
    photos: list[str] = Field(default_factory=list, max_length=10)
    adherence: Adherence | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("measurements")
    @classmethod
    def _sane_measurements(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("too many measurements")
        for name, value in v.items():
            if not (0 < len(name) <= 60):
                raise ValueError("measurement names must be 1-60 characters")
            if not (0 < value <= 500):
                raise ValueError(f"measurement {name!r} out of range")
        return v


class CheckInOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    check_in_date: date
    weight: float | None
    weight_unit: str | None
    measurements: dict[str, float] | None
    photos: list[str]
    adherence: Adherence | None
    notes: str | None
    created_at: datetime


class PhotoUploadOut(BaseModel):
    key: str


class ExerciseLite(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    video_url: str | None


class ClientProgramOut(BaseModel):
    """The client app's one-shot payload: assigned program tree plus the
    exercises it references (cached locally for offline use)."""

    program: ProgramDetailOut
    exercises: list[ExerciseLite]
