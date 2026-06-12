import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import CurrentTrainer
from app.models.client import Client
from app.models.exercise import Exercise
from app.models.program import Prescription, Program, ProgramBlock, ProgramDay, ProgramWeek
from app.schemas.program import (
    ProgramCreate,
    ProgramDetailOut,
    ProgramDuplicate,
    ProgramOut,
    ProgramStructureIn,
    ProgramUpdate,
)

router = APIRouter(prefix="/programs", tags=["programs"])

DbSession = Annotated[Session, Depends(get_db)]

_FULL_TREE = (
    selectinload(Program.blocks)
    .selectinload(ProgramBlock.weeks)
    .selectinload(ProgramWeek.days)
    .selectinload(ProgramDay.prescriptions),
)


def _get_program_or_404(
    db: Session, trainer_id: uuid.UUID, program_id: uuid.UUID, *, with_tree: bool = False
) -> Program:
    query = select(Program).where(Program.id == program_id, Program.trainer_id == trainer_id)
    if with_tree:
        query = query.options(*_FULL_TREE)
    program = db.scalar(query)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return program


def _validate_client_ref(
    db: Session, trainer_id: uuid.UUID, client_id: uuid.UUID | None
) -> None:
    if client_id is None:
        return
    client = db.scalar(
        select(Client).where(Client.id == client_id, Client.trainer_id == trainer_id)
    )
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Client not found"
        )


def _validate_exercise_refs(
    db: Session, trainer_id: uuid.UUID, structure: ProgramStructureIn
) -> None:
    wanted = {
        prescription.exercise_id
        for block in structure.blocks
        for week in block.weeks
        for day in week.days
        for prescription in day.prescriptions
    }
    if not wanted:
        return
    allowed = set(
        db.scalars(
            select(Exercise.id).where(
                Exercise.id.in_(wanted),
                or_(Exercise.trainer_id.is_(None), Exercise.trainer_id == trainer_id),
            )
        )
    )
    missing = wanted - allowed
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown exercise id(s): {', '.join(str(m) for m in sorted(missing))}",
        )


def _bad_child_id(kind: str, child_id: uuid.UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"Unknown {kind} id for this program: {child_id}",
    )


def _reconcile(existing: list, items: list, kind: str, build, update) -> list:
    """Generic child-list upsert: items with an id update the matching existing
    child (ids from elsewhere are rejected), items without an id are created,
    unreferenced children are dropped (delete-orphan), order = list order."""
    by_id = {child.id: child for child in existing}
    result = []
    for index, item in enumerate(items):
        if item.id is not None:
            child = by_id.get(item.id)
            if child is None:
                raise _bad_child_id(kind, item.id)
        else:
            child = build()
        update(child, item)
        child.position = index
        result.append(child)
    return result


def _apply_structure(program: Program, structure: ProgramStructureIn) -> None:
    def update_prescription(row: Prescription, item) -> None:
        row.exercise_id = item.exercise_id
        row.sets = item.sets
        row.rep_scheme = item.rep_scheme.model_dump()
        row.load_scheme = item.load_scheme.model_dump() if item.load_scheme else None
        row.tempo = item.tempo
        row.rest_seconds = item.rest_seconds
        row.notes = item.notes

    def update_day(row: ProgramDay, item) -> None:
        row.name = item.name
        row.is_rest_day = item.is_rest_day
        row.notes = item.notes
        row.prescriptions = _reconcile(
            row.prescriptions, item.prescriptions, "prescription", Prescription, update_prescription
        )

    def update_week(row: ProgramWeek, item) -> None:
        row.name = item.name
        row.days = _reconcile(row.days, item.days, "day", ProgramDay, update_day)

    def update_block(row: ProgramBlock, item) -> None:
        row.name = item.name
        row.notes = item.notes
        row.weeks = _reconcile(row.weeks, item.weeks, "week", ProgramWeek, update_week)

    program.blocks = _reconcile(
        program.blocks, structure.blocks, "block", ProgramBlock, update_block
    )


@router.post("", response_model=ProgramDetailOut, status_code=status.HTTP_201_CREATED)
def create_program(payload: ProgramCreate, trainer: CurrentTrainer, db: DbSession):
    if payload.is_template and payload.client_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Templates cannot be assigned to a client",
        )
    _validate_client_ref(db, trainer.id, payload.client_id)
    program = Program(trainer_id=trainer.id, **payload.model_dump())
    db.add(program)
    db.commit()
    return _get_program_or_404(db, trainer.id, program.id, with_tree=True)


@router.get("", response_model=list[ProgramOut])
def list_programs(
    trainer: CurrentTrainer,
    db: DbSession,
    client_id: uuid.UUID | None = None,
    is_template: bool | None = None,
):
    query = (
        select(Program)
        .where(Program.trainer_id == trainer.id)
        .order_by(Program.updated_at.desc())
    )
    if client_id is not None:
        query = query.where(Program.client_id == client_id)
    if is_template is not None:
        query = query.where(Program.is_template == is_template)
    return db.scalars(query).all()


@router.get("/{program_id}", response_model=ProgramDetailOut)
def get_program(program_id: uuid.UUID, trainer: CurrentTrainer, db: DbSession):
    return _get_program_or_404(db, trainer.id, program_id, with_tree=True)


@router.patch("/{program_id}", response_model=ProgramOut)
def update_program(
    program_id: uuid.UUID, payload: ProgramUpdate, trainer: CurrentTrainer, db: DbSession
):
    program = _get_program_or_404(db, trainer.id, program_id)
    updates = payload.model_dump(exclude_unset=True)
    if "client_id" in updates:
        _validate_client_ref(db, trainer.id, updates["client_id"])
    is_template = updates.get("is_template", program.is_template)
    client_id = updates.get("client_id", program.client_id)
    if is_template and client_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Templates cannot be assigned to a client",
        )
    for field, value in updates.items():
        setattr(program, field, value)
    db.commit()
    db.refresh(program)
    return program


@router.put("/{program_id}/structure", response_model=ProgramDetailOut)
def replace_structure(
    program_id: uuid.UUID,
    structure: ProgramStructureIn,
    trainer: CurrentTrainer,
    db: DbSession,
):
    program = _get_program_or_404(db, trainer.id, program_id, with_tree=True)
    _validate_exercise_refs(db, trainer.id, structure)
    _apply_structure(program, structure)
    program.updated_at = func.now()  # touch parent even when only children changed
    db.commit()
    db.expire_all()
    return _get_program_or_404(db, trainer.id, program_id, with_tree=True)


@router.post(
    "/{program_id}/duplicate", response_model=ProgramDetailOut, status_code=status.HTTP_201_CREATED
)
def duplicate_program(
    program_id: uuid.UUID, payload: ProgramDuplicate, trainer: CurrentTrainer, db: DbSession
):
    """Deep-copies the program. as_template saves it to the template library;
    otherwise an optional client_id assigns the copy (how templates get used)."""
    source = _get_program_or_404(db, trainer.id, program_id, with_tree=True)
    if payload.as_template and payload.client_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Templates cannot be assigned to a client",
        )
    _validate_client_ref(db, trainer.id, payload.client_id)

    copy = Program(
        trainer_id=trainer.id,
        client_id=None if payload.as_template else payload.client_id,
        name=payload.name or f"{source.name} (copy)",
        description=source.description,
        is_template=payload.as_template,
        version=source.version + 1,
        source_program_id=source.id,
        starts_on=None,
        blocks=[
            ProgramBlock(
                name=block.name,
                notes=block.notes,
                position=block.position,
                weeks=[
                    ProgramWeek(
                        name=week.name,
                        position=week.position,
                        days=[
                            ProgramDay(
                                name=day.name,
                                is_rest_day=day.is_rest_day,
                                notes=day.notes,
                                position=day.position,
                                prescriptions=[
                                    Prescription(
                                        exercise_id=p.exercise_id,
                                        position=p.position,
                                        sets=p.sets,
                                        rep_scheme=p.rep_scheme,
                                        load_scheme=p.load_scheme,
                                        tempo=p.tempo,
                                        rest_seconds=p.rest_seconds,
                                        notes=p.notes,
                                    )
                                    for p in day.prescriptions
                                ],
                            )
                            for day in week.days
                        ],
                    )
                    for week in block.weeks
                ],
            )
            for block in source.blocks
        ],
    )
    db.add(copy)
    db.commit()
    return _get_program_or_404(db, trainer.id, copy.id, with_tree=True)


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(program_id: uuid.UUID, trainer: CurrentTrainer, db: DbSession) -> Response:
    program = _get_program_or_404(db, trainer.id, program_id)
    db.delete(program)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
