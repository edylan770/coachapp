import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.trainer import Trainer
from app.models.user import User


class ClientStatus(enum.StrEnum):
    invited = "invited"
    active = "active"
    paused = "paused"


class Client(Base):
    """A trainer's client. Created by the trainer (invite-only); `user_id` is
    linked once the client accepts the invite and gets an account."""

    __tablename__ = "clients"
    __table_args__ = (
        # A trainer can't invite the same email twice; different trainers can.
        UniqueConstraint("trainer_id", "email", name="uq_clients_trainer_id_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    trainer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(
            ClientStatus,
            name="client_status",
            native_enum=False,
            length=20,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        server_default=ClientStatus.invited.value,
    )
    # Invite tokens are opaque, stored hashed, and cleared on acceptance.
    invite_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Check-in cadence ("scheduled cadence per client", spec §3); due-date
    # logic = last check-in + cadence, computed in queries.
    checkin_cadence_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("7")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    trainer: Mapped[Trainer] = relationship()
    user: Mapped[User | None] = relationship()

    @property
    def has_account(self) -> bool:
        return self.user_id is not None
