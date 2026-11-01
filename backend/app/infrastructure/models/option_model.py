import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.models.poll_model import PollModel
    from app.infrastructure.models.vote_selection_model import VoteSelectionModel

class OptionModel(Base):
    __tablename__ = "options"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    poll_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    text: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    poll: Mapped["PollModel"] = relationship(
        back_populates="options"
    )

    vote_selections: Mapped[list["VoteSelectionModel"]] = relationship(
        back_populates="option"
    )