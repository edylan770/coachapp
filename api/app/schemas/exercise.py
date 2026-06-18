import uuid

from pydantic import BaseModel, ConfigDict, Field


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    video_url: str | None = Field(default=None, max_length=500)
    # Set to a *global* exercise id to override (shadow) it in your library.
    parent_exercise_id: uuid.UUID | None = None


class ExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    video_url: str | None = Field(default=None, max_length=500)


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    video_url: str | None
    parent_exercise_id: uuid.UUID | None
    is_custom: bool
