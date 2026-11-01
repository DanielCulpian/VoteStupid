import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from typing import TYPE_CHECKING

from app.infrastructure.models.base import Base

from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.infrastructure.models.poll_model import PollModel
    from app.infrastructure.models.vote_selection_model import VoteSelectionModel

class VoteModel(Base):
    __tablename__ = "votes"

    __table_args__ = (
        UniqueConstraint(
            "poll_id",
            "voter_token_hash",
            name="uq_vote_poll_voter"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    poll_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    voter_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    poll: Mapped["PollModel"] = relationship(
        back_populates="votes"
    )

    selections: Mapped[list["VoteSelectionModel"]] = relationship(
        back_populates="vote",
        cascade="all, delete-orphan"
    )