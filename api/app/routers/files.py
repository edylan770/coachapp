import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.models.client import Client
from app.models.trainer import Trainer
from app.storage import get_storage

router = APIRouter(tags=["files"])

_KEY_RE = re.compile(r"checkins/([0-9a-f-]{36})/[0-9a-f-]{36}\.(jpg|png|webp|heic)")
_MEDIA_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "heic": "image/heic",
}


@router.get("/files/{key:path}")
def get_file(key: str, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    """Serves stored photos to the owning client or their trainer only."""
    not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    match = _KEY_RE.fullmatch(key)
    if match is None:
        raise not_found
    client = db.get(Client, uuid.UUID(match.group(1)))
    if client is None:
        raise not_found

    is_owner = client.user_id == current_user.id
    is_their_trainer = (
        db.scalar(
            select(Trainer.id).where(
                Trainer.id == client.trainer_id, Trainer.user_id == current_user.id
            )
        )
        is not None
    )
    if not (is_owner or is_their_trainer):
        raise not_found

    try:
        data = get_storage().load(key)
    except FileNotFoundError:
        raise not_found from None
    return Response(content=data, media_type=_MEDIA_TYPES[match.group(2)])
