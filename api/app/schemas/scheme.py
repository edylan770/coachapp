"""Typed rep/load schemes stored as JSONB on prescriptions.

Discriminated unions keep the storage flexible (one JSONB column) while every
variant stays strictly validated — the "flexible but typed" structure the spec
requires. Designed to be niche-agnostic: %1RM waves (powerlifting), RPE/RIR
(bodybuilding), absolute loads, bodyweight and duration work (general fitness).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# --- rep schemes ---


class FixedReps(BaseModel):
    type: Literal["fixed"]
    reps: int = Field(ge=1, le=500)


class RepRange(BaseModel):
    type: Literal["range"]
    min: int = Field(ge=1, le=500)
    max: int = Field(ge=1, le=500)

    @model_validator(mode="after")
    def _min_not_above_max(self) -> "RepRange":
        if self.min > self.max:
            raise ValueError("min reps cannot exceed max reps")
        return self


class Amrap(BaseModel):
    """As many reps as possible."""

    type: Literal["amrap"]


class DurationReps(BaseModel):
    """Time-based sets (planks, carries, intervals)."""

    type: Literal["duration"]
    seconds: int = Field(ge=1, le=86400)


RepScheme = Annotated[
    FixedReps | RepRange | Amrap | DurationReps,
    Field(discriminator="type"),
]


# --- load schemes ---


class AbsoluteLoad(BaseModel):
    type: Literal["absolute"]
    weight: float = Field(ge=0, le=2000)
    unit: Literal["kg", "lb"]


class Percent1RMLoad(BaseModel):
    type: Literal["percent_1rm"]
    percent: float = Field(ge=1, le=200)


class RpeLoad(BaseModel):
    type: Literal["rpe"]
    rpe: float = Field(ge=1, le=10)


class RirLoad(BaseModel):
    """Reps in reserve."""

    type: Literal["rir"]
    rir: int = Field(ge=0, le=10)


class BodyweightLoad(BaseModel):
    type: Literal["bodyweight"]


LoadScheme = Annotated[
    AbsoluteLoad | Percent1RMLoad | RpeLoad | RirLoad | BodyweightLoad,
    Field(discriminator="type"),
]
