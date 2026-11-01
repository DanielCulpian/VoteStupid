import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base

from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.infrastructure.models.option_model import OptionModel
    from app.infrastructure.models.vote_model import VoteModel

class PollModel(Base):
    __tablename__ = "polls"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    poll_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    max_selections: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    closes_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    options: Mapped[list["OptionModel"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan"
    )

    votes: Mapped[list["VoteModel"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan"
    )