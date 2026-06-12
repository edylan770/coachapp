import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CheckIn(Base):
    """A client's periodic check-in. Photos are object-storage keys; review
    workflow fields (AI drafts, trainer response) arrive in Phase 4."""

    __tablename__ = "check_ins"
    __table_args__ = (
        UniqueConstraint("client_id", "check_in_date", name="uq_check_ins_client_id_check_in_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight: Mapped[float | None] = mapped_column(Float)
    weight_unit: Mapped[str | None] = mapped_column(String(2))
    # Free-form name -> value map (e.g. {"waist": 81.5}); unit convention is
    # the client/trainer's own.
    measurements: Mapped[dict | None] = mapped_column(JSONB)
    photos: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    # {"training": 1-5, "nutrition": 1-5, "sleep": 1-5}
    adherence: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
