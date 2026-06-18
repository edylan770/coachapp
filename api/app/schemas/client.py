import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.client import ClientStatus


class ClientCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)


class ClientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    # Email is editable only while the invite is pending (no account yet).
    email: EmailStr | None = None
    # invited→active happens via invite acceptance, never via PATCH.
    status: Literal["active", "paused"] | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    status: ClientStatus
    has_account: bool
    invite_expires_at: datetime | None
    created_at: datetime


class ClientInviteOut(ClientOut):
    """Returned only from invite/reinvite — the plaintext token is shown once."""

    invite_token: str


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=72)
