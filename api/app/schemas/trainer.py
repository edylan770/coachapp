import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrainerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    business_name: str | None = Field(default=None, max_length=120)
    bio: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    settings: dict | None = None


class TrainerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    business_name: str | None
    bio: str | None
    logo_url: str | None
    settings: dict
    created_at: datetime
