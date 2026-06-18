import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentTrainer
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate, ExerciseOut, ExerciseUpdate

router = APIRouter(prefix="/exercises", tags=["exercises"])

DbSession = Annotated[Session, Depends(get_db)]

_DUPLICATE_NAME = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="You already have an exercise with this name",
)


@router.get("", response_model=list[ExerciseOut])
def list_exercises(trainer: CurrentTrainer, db: DbSession):
    """The trainer's effective library: global exercises plus their customs.
    Globals overridden by one of the trainer's customs are hidden."""
    visible = db.scalars(
        select(Exercise)
        .where(or_(Exercise.trainer_id.is_(None), Exercise.trainer_id == trainer.id))
        .order_by(Exercise.name)
    ).all()
    shadowed = {e.parent_exercise_id for e in visible if e.trainer_id and e.parent_exercise_id}
    return [e for e in visible if e.id not in shadowed]


@router.post("", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(payload: ExerciseCreate, trainer: CurrentTrainer, db: DbSession):
    if payload.parent_exercise_id is not None:
        parent = db.get(Exercise, payload.parent_exercise_id)
        if parent is None or parent.trainer_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="parent_exercise_id must reference a global exercise",
            )
    exercise = Exercise(trainer_id=trainer.id, **payload.model_dump())
    db.add(exercise)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _DUPLICATE_NAME from None
    db.refresh(exercise)
    return exercise


@router.get("/{exercise_id}", response_model=ExerciseOut)
def get_exercise(exercise_id: uuid.UUID, trainer: CurrentTrainer, db: DbSession):
    exercise = db.get(Exercise, exercise_id)
    if exercise is None or (exercise.trainer_id is not None and exercise.trainer_id != trainer.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return exercise


def _get_own_exercise(db: Session, trainer_id: uuid.UUID, exercise_id: uuid.UUID) -> Exercise:
    exercise = db.get(Exercise, exercise_id)
    if exercise is None or (exercise.trainer_id is not None and exercise.trainer_id != trainer_id):
        # Other trainers' customs are invisible.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    if exercise.trainer_id is None:
        # Globals are visible but read-only; override via parent_exercise_id.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global exercises are read-only — create an override instead",
        )
    return exercise


@router.patch("/{exercise_id}", response_model=ExerciseOut)
def update_exercise(
    exercise_id: uuid.UUID, payload: ExerciseUpdate, trainer: CurrentTrainer, db: DbSession
):
    exercise = _get_own_exercise(db, trainer.id, exercise_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exercise, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _DUPLICATE_NAME from None
    db.refresh(exercise)
    return exercise


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: uuid.UUID, trainer: CurrentTrainer, db: DbSession) -> Response:
    exercise = _get_own_exercise(db, trainer.id, exercise_id)
    db.delete(exercise)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exercise is used by a program and cannot be deleted",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
