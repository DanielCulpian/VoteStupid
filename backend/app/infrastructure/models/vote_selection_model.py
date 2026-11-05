import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.models.vote_model import VoteModel
    from app.infrastructure.models.option_model import OptionModel

class VoteSelectionModel(Base):
    __tablename__ = "vote_selections"

    __table_args__ = (
        UniqueConstraint(
            "vote_id",
            "option_id",
            name="uq_vote_selection_option"
        ),
        UniqueConstraint(
            "vote_id",
            "position",
            name="uq_vote_selection_position"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    vote_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("votes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("options.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    position: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    vote: Mapped["VoteModel"] = relationship(
        back_populates="selections"
    )

    option: Mapped["OptionModel"] = relationship(
        back_populates="vote_selections"
    )