import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import security
from app.db import get_db
from app.models.client import Client
from app.models.trainer import Trainer
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = security.decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _unauthorized() from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_trainer(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Trainer:
    """Tenancy anchor: every trainer-facing endpoint resolves the caller to a
    Trainer row and filters all queries by its id. Never trust ids from the
    request body for scoping."""
    if current_user.role != UserRole.trainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Trainer role required"
        )
    trainer = db.scalar(select(Trainer).where(Trainer.user_id == current_user.id))
    if trainer is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Trainer profile not found"
        )
    return trainer


CurrentTrainer = Annotated[Trainer, Depends(get_current_trainer)]


def get_current_client(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Client:
    """Tenancy anchor for the client app's /me endpoints."""
    if current_user.role != UserRole.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client role required")
    client = db.scalar(select(Client).where(Client.user_id == current_user.id))
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Client record not found"
        )
    return client


CurrentClient = Annotated[Client, Depends(get_current_client)]
