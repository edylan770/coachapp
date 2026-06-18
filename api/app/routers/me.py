import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.deps import CurrentClient
from app.models.check_in import CheckIn
from app.models.client import Client
from app.models.exercise import Exercise
from app.models.program import Prescription, Program, ProgramBlock, ProgramDay, ProgramWeek
from app.models.workout_log import SetLog, WorkoutLog
from app.queries import PROGRAM_FULL_TREE
from app.schemas.check_in import CheckInCreate, CheckInOut, ClientProgramOut, PhotoUploadOut
from app.schemas.workout_log import (
    SyncRequest,
    SyncResponse,
    SyncResultItem,
    WorkoutLogIn,
    WorkoutLogOut,
)
from app.storage import get_storage

router = APIRouter(prefix="/me", tags=["client-app"])

DbSession = Annotated[Session, Depends(get_db)]

_ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}


# --- program ---


@router.get("/program", response_model=ClientProgramOut)
def my_program(client: CurrentClient, db: DbSession):
    """The client's current program (most recently updated assignment) plus
    every exercise it references — cached by the app for offline use."""
    program = db.scalar(
        select(Program)
        .where(Program.client_id == client.id, Program.is_template.is_(False))
        .order_by(Program.updated_at.desc())
        .options(*PROGRAM_FULL_TREE)
        .limit(1)
    )
    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No program assigned yet"
        )
    exercise_ids = {
        rx.exercise_id
        for block in program.blocks
        for week in block.weeks
        for day in week.days
        for rx in day.prescriptions
    }
    exercises = (
        db.scalars(select(Exercise).where(Exercise.id.in_(exercise_ids))).all()
        if exercise_ids
        else []
    )
    return {"program": program, "exercises": exercises}


# --- workout log sync ---


class _Rejected(Exception):
    def __init__(self, reason: str):
        self.reason = reason


def _existing_day_id(db: Session, client: Client, day_id: uuid.UUID | None) -> uuid.UUID | None:
    """Keeps the link only if the day still belongs to one of this client's
    programs; stale references (program edited/unassigned) are nulled, never
    rejected — the denormalized snapshot keeps history readable."""
    if day_id is None:
        return None
    found = db.scalar(
        select(ProgramDay.id)
        .join(ProgramWeek, ProgramDay.week_id == ProgramWeek.id)
        .join(ProgramBlock, ProgramWeek.block_id == ProgramBlock.id)
        .join(Program, ProgramBlock.program_id == Program.id)
        .where(ProgramDay.id == day_id, Program.client_id == client.id)
    )
    return found


def _existing_prescription_id(
    db: Session, client: Client, prescription_id: uuid.UUID | None
) -> uuid.UUID | None:
    if prescription_id is None:
        return None
    found = db.scalar(
        select(Prescription.id)
        .join(ProgramDay, Prescription.day_id == ProgramDay.id)
        .join(ProgramWeek, ProgramDay.week_id == ProgramWeek.id)
        .join(ProgramBlock, ProgramWeek.block_id == ProgramBlock.id)
        .join(Program, ProgramBlock.program_id == Program.id)
        .where(Prescription.id == prescription_id, Program.client_id == client.id)
    )
    return found


def _existing_exercise_id(
    db: Session, client: Client, exercise_id: uuid.UUID | None
) -> uuid.UUID | None:
    if exercise_id is None:
        return None
    return db.scalar(
        select(Exercise.id).where(
            Exercise.id == exercise_id,
            or_(Exercise.trainer_id.is_(None), Exercise.trainer_id == client.trainer_id),
        )
    )


def _upsert_workout_log(db: Session, client: Client, item: WorkoutLogIn) -> bool:
    """Returns True if created, False if updated. Raises _Rejected."""
    existing = db.get(WorkoutLog, item.id)
    if existing is not None and existing.client_id != client.id:
        raise _Rejected("workout log id is not available")

    log = existing or WorkoutLog(id=item.id, client_id=client.id)
    log.program_day_id = _existing_day_id(db, client, item.program_day_id)
    log.workout_date = item.workout_date
    log.notes = item.notes
    log.started_at = item.started_at
    log.completed_at = item.completed_at

    # Reject set ids that exist under any other workout log (or are duplicated
    # in the payload) before flush, instead of bouncing off the PK constraint.
    payload_set_ids = [s.id for s in item.set_logs]
    if len(set(payload_set_ids)) != len(payload_set_ids):
        raise _Rejected("duplicate set log ids in payload")
    if payload_set_ids:
        claimed = db.execute(
            select(SetLog.id, SetLog.workout_log_id).where(SetLog.id.in_(payload_set_ids))
        ).all()
        if any(owner_id != log.id for _, owner_id in claimed):
            raise _Rejected("set log id is not available")

    existing_sets = {s.id: s for s in log.set_logs}
    new_sets: list[SetLog] = []
    for set_item in item.set_logs:
        row = existing_sets.get(set_item.id)
        if row is None:
            row = SetLog(id=set_item.id)
        row.prescription_id = _existing_prescription_id(db, client, set_item.prescription_id)
        row.exercise_id = _existing_exercise_id(db, client, set_item.exercise_id)
        row.exercise_name = set_item.exercise_name
        row.position = set_item.position
        row.set_number = set_item.set_number
        row.weight = set_item.weight
        row.weight_unit = set_item.weight_unit
        row.reps = set_item.reps
        row.duration_seconds = set_item.duration_seconds
        row.rpe = set_item.rpe
        row.is_completed = set_item.is_completed
        row.prescribed_snapshot = set_item.prescribed_snapshot
        new_sets.append(row)
    log.set_logs = new_sets

    if existing is None:
        db.add(log)
    return existing is None


@router.post("/sync", response_model=SyncResponse)
def sync_workout_logs(payload: SyncRequest, client: CurrentClient, db: DbSession):
    """Idempotent batch upsert. Items fail independently (savepoints) so one
    bad record never blocks the rest of an offline queue."""
    results: list[SyncResultItem] = []
    for item in payload.workout_logs:
        try:
            with db.begin_nested():
                created = _upsert_workout_log(db, client, item)
            results.append(
                SyncResultItem(id=item.id, status="created" if created else "updated")
            )
        except _Rejected as exc:
            results.append(SyncResultItem(id=item.id, status="rejected", detail=exc.reason))
        except IntegrityError:
            results.append(
                SyncResultItem(id=item.id, status="rejected", detail="constraint violation")
            )
    db.commit()
    return SyncResponse(results=results)


@router.get("/workout-logs", response_model=list[WorkoutLogOut])
def my_workout_logs(
    client: CurrentClient,
    db: DbSession,
    since: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
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


# --- check-ins ---


@router.post("/check-ins/photos", response_model=PhotoUploadOut)
def upload_checkin_photo(file: UploadFile, client: CurrentClient):
    ext = _ALLOWED_PHOTO_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported image type (use jpeg/png/webp/heic)",
        )
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo exceeds {get_settings().max_upload_mb}MB limit",
        )
    key = f"checkins/{client.id}/{uuid.uuid4()}{ext}"
    get_storage().save(key, data)
    return PhotoUploadOut(key=key)


@router.post("/check-ins", response_model=CheckInOut, status_code=status.HTTP_201_CREATED)
def submit_check_in(
    payload: CheckInCreate, client: CurrentClient, db: DbSession, response: Response
):
    if payload.id is not None:
        existing = db.get(CheckIn, payload.id)
        if existing is not None:
            if existing.client_id != client.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="check-in id is not available"
                )
            response.status_code = status.HTTP_200_OK  # idempotent retry
            return existing

    prefix = f"checkins/{client.id}/"
    if any(not key.startswith(prefix) for key in payload.photos):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="photos must reference your own uploads",
        )

    check_in = CheckIn(
        client_id=client.id,
        check_in_date=payload.check_in_date,
        weight=payload.weight,
        weight_unit=payload.weight_unit if payload.weight is not None else None,
        measurements=payload.measurements,
        photos=payload.photos,
        adherence=payload.adherence.model_dump(exclude_none=True) if payload.adherence else None,
        notes=payload.notes,
    )
    if payload.id is not None:
        check_in.id = payload.id
    db.add(check_in)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A check-in for this date was already submitted",
        ) from None
    db.refresh(check_in)
    return check_in


@router.get("/check-ins", response_model=list[CheckInOut])
def my_check_ins(
    client: CurrentClient,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return db.scalars(
        select(CheckIn)
        .where(CheckIn.client_id == client.id)
        .order_by(CheckIn.check_in_date.desc())
        .limit(limit)
    ).all()
