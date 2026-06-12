import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import security
from app.config import get_settings
from app.db import get_db
from app.deps import CurrentTrainer
from app.models.check_in import CheckIn
from app.models.client import Client, ClientStatus
from app.models.workout_log import WorkoutLog
from app.schemas.check_in import CheckInOut
from app.schemas.client import ClientCreate, ClientInviteOut, ClientOut, ClientUpdate
from app.schemas.workout_log import WorkoutLogOut

router = APIRouter(prefix="/clients", tags=["clients"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_client_or_404(db: Session, trainer_id: uuid.UUID, client_id: uuid.UUID) -> Client:
    client = db.scalar(
        select(Client).where(Client.id == client_id, Client.trainer_id == trainer_id)
    )
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def _arm_invite(client: Client) -> str:
    """Generates a fresh invite token (returned in plaintext exactly once)."""
    raw = security.generate_refresh_token()
    client.invite_token_hash = security.hash_refresh_token(raw)
    client.invite_expires_at = datetime.now(UTC) + timedelta(
        days=get_settings().invite_ttl_days
    )
    return raw


def _invite_response(client: Client, raw_token: str) -> ClientInviteOut:
    return ClientInviteOut(
        **ClientOut.model_validate(client).model_dump(), invite_token=raw_token
    )


@router.post("", response_model=ClientInviteOut, status_code=status.HTTP_201_CREATED)
def invite_client(payload: ClientCreate, trainer: CurrentTrainer, db: DbSession):
    """Creates a client in `invited` status. v1 has no email delivery — the
    trainer shares the returned invite token/link themselves."""
    client = Client(
        trainer_id=trainer.id,
        email=payload.email.strip().lower(),
        full_name=payload.full_name,
    )
    raw_token = _arm_invite(client)
    db.add(client)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a client with this email",
        ) from None
    db.refresh(client)
    return _invite_response(client, raw_token)


@router.get("", response_model=list[ClientOut])
def list_clients(
    trainer: CurrentTrainer, db: DbSession, status_filter: ClientStatus | None = None
):
    query = select(Client).where(Client.trainer_id == trainer.id).order_by(Client.created_at)
    if status_filter is not None:
        query = query.where(Client.status == status_filter)
    return db.scalars(query).all()


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: uuid.UUID, trainer: CurrentTrainer, db: DbSession):
    return _get_client_or_404(db, trainer.id, client_id)


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: uuid.UUID, payload: ClientUpdate, trainer: CurrentTrainer, db: DbSession
):
    client = _get_client_or_404(db, trainer.id, client_id)
    updates = payload.model_dump(exclude_unset=True)

    if "email" in updates:
        if client.has_account:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email cannot be changed after the client has an account",
            )
        client.email = updates.pop("email").strip().lower()
    if "status" in updates:
        if not client.has_account:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Client has not accepted their invite yet",
            )
        client.status = ClientStatus(updates.pop("status"))
    for field, value in updates.items():
        setattr(client, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a client with this email",
        ) from None
    db.refresh(client)
    return client


@router.post("/{client_id}/reinvite", response_model=ClientInviteOut)
def reinvite_client(client_id: uuid.UUID, trainer: CurrentTrainer, db: DbSession):
    client = _get_client_or_404(db, trainer.id, client_id)
    if client.has_account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client already accepted their invite",
        )
    raw_token = _arm_invite(client)
    db.commit()
    db.refresh(client)
    return _invite_response(client, raw_token)


@router.get("/{client_id}/workout-logs", response_model=list[WorkoutLogOut])
def client_workout_logs(
    client_id: uuid.UUID,
    trainer: CurrentTrainer,
    db: DbSession,
    since: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    client = _get_client_or_404(db, trainer.id, client_id)
    query = (
        select(WorkoutLog)
        .where(WorkoutLog.client_id == client.id)
        .order_by(WorkoutLog.workout_date.desc(), WorkoutLog.created_at.desc())
        .options(selectinload(WorkoutLog.set_logs))
        .limit(limit)
    )
    if since is not None:
        query = query.where(WorkoutLog.workout_date >= since)
    return db.scalars(query).all()


@router.get("/{client_id}/check-ins", response_model=list[CheckInOut])
def client_check_ins(
    client_id: uuid.UUID,
    trainer: CurrentTrainer,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    client = _get_client_or_404(db, trainer.id, client_id)
    return db.scalars(
        select(CheckIn)
        .where(CheckIn.client_id == client.id)
        .order_by(CheckIn.check_in_date.desc())
        .limit(limit)
    ).all()


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: uuid.UUID, trainer: CurrentTrainer, db: DbSession) -> Response:
    """Deletes the client and, if they had an account, the account too (their
    user row cascades to this client row). Assigned programs survive with
    client_id set NULL."""
    client = _get_client_or_404(db, trainer.id, client_id)
    if client.user is not None:
        db.delete(client.user)
    else:
        db.delete(client)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
