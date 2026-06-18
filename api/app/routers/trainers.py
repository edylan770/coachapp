from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentTrainer
from app.models.trainer import Trainer
from app.schemas.trainer import TrainerOut, TrainerUpdate

router = APIRouter(prefix="/trainers", tags=["trainers"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/me", response_model=TrainerOut)
def get_my_profile(trainer: CurrentTrainer) -> Trainer:
    return trainer


@router.patch("/me", response_model=TrainerOut)
def update_my_profile(payload: TrainerUpdate, trainer: CurrentTrainer, db: DbSession) -> Trainer:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(trainer, field, value)
    db.commit()
    db.refresh(trainer)
    return trainer
