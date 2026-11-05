from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domain.entities.poll import Poll
from app.domain.entities.vote import Vote
from app.domain.repositories.poll_repository import PollRepository
from app.domain.vote_rule_error import VoteRuleError

from app.infrastructure.mappers.poll_mapper import to_entity as poll_to_entity
from app.infrastructure.mappers.poll_mapper import to_model as poll_to_model
from app.infrastructure.mappers.vote_mapper import to_entity as vote_to_entity
from app.infrastructure.mappers.vote_mapper import to_model as vote_to_model

from app.infrastructure.models.option_model import OptionModel
from app.infrastructure.models.poll_model import PollModel
from app.infrastructure.models.vote_model import VoteModel
from app.infrastructure.models.vote_selection_model import VoteSelectionModel

class SqlAlchemyPollRepository(PollRepository):

    def list_polls(self, state="all", poll_type=None, offset=0, limit=24):
        """Filter and sort open polls first, then recent polls, respecting scheduled closing times."""
        active = and_(PollModel.is_active.is_(True), or_(PollModel.closes_at.is_(None), PollModel.closes_at > datetime.now(timezone.utc)))
        filters = []
        if state != "all":
            filters.append(active if state == "active" else ~active)
        if poll_type:
            filters.append(PollModel.poll_type == poll_type)
        total = self.session.scalar(select(func.count()).select_from(PollModel).where(*filters))
        rows = self.session.scalars(select(PollModel).options(selectinload(PollModel.options)).where(*filters)
            .order_by(case((active, 0), else_=1), PollModel.created_at.desc(), PollModel.id.desc())
            .offset(offset).limit(limit)).all()
        return [poll_to_entity(row) for row in rows], total

    def __init__(self, session: Session):
        """Bind the repository to the supplied SQLAlchemy session."""
        self.session = session

    def _commit(self) -> None:
        """Commit the transaction and roll it back if an error occurs."""
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_by_id(self, poll_id: UUID) -> Poll | None:
        """Retrieve a poll by its identifier, or return None if it does not exist."""
        statement = (
            select(PollModel)
            .options(selectinload(PollModel.options))
            .where(PollModel.id == poll_id)
        )

        poll_model = self.session.execute(statement).scalar_one_or_none()

        if poll_model is None:
            return None

        return poll_to_entity(poll_model)

    def get_vote_by_voter(
        self,
        poll_id: UUID,
        voter_token_hash: str
    ) -> Vote | None:
        """Find a participant's vote using the poll and the hash of their token."""
        statement = (
            select(VoteModel)
            .options(selectinload(VoteModel.selections))
            .where(
                VoteModel.poll_id == poll_id,
                VoteModel.voter_token_hash == voter_token_hash
            )
        )

        vote_model = self.session.execute(statement).scalar_one_or_none()

        if vote_model is None:
            return None

        return vote_to_entity(vote_model)

    def save_vote(self, vote: Vote) -> None:
        """Save a vote and convert concurrent duplicates into an already-voted conflict."""
        vote_model = vote_to_model(vote)
        self.session.add(vote_model)
        try:
            self._commit()
        except IntegrityError as error:
            if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "uq_vote_poll_voter":
                raise VoteRuleError("Este participante ya ha votado.") from error
            raise

    def update_vote(self, vote: Vote) -> None:
        """Replace the existing vote selections and persist the modification timestamp."""
        statement = (
            select(VoteModel)
            .options(selectinload(VoteModel.selections))
            .where(VoteModel.id == vote.id)
        )

        vote_model = self.session.execute(statement).scalar_one_or_none()

        if vote_model is None:
            raise ValueError("El voto que se intenta actualizar no existe.")

        # Delete the previous selections and persist that change.
        vote_model.selections.clear()
        self.session.flush()

        # Create the new selections on the existing vote.
        vote_model.selections = [
            VoteSelectionModel(
                option_id=option_id,
                position=position
            )
            for position, option_id in enumerate(vote.selected_option_ids)
        ]

        vote_model.updated_at = vote.updated_at

        self._commit()

    def get_options_by_ids(
        self,
        poll_id: UUID,
        option_ids: list[UUID]
    ) -> list[UUID]:
        """Return the requested identifiers that belong to the poll, in their original order."""
        if not option_ids:
            return []

        statement = select(OptionModel.id).where(
            OptionModel.poll_id == poll_id,
            OptionModel.id.in_(option_ids)
        )

        found_ids = set(self.session.execute(statement).scalars().all())

        return [
            option_id
            for option_id in option_ids
            if option_id in found_ids
        ]

    def update_poll(self, poll: Poll) -> None:
        """Update a poll and its options without deleting options that have votes."""
        statement = (
            select(PollModel)
            .options(selectinload(PollModel.options))
            .where(PollModel.id == poll.id)
        )

        poll_model = self.session.execute(statement).scalar_one_or_none()

        if poll_model is None:
            raise ValueError("La votación que se intenta actualizar no existe.")

        existing_options = {
            option.id: option
            for option in poll_model.options
        }

        updated_option_ids = {
            option.id
            for option in poll.options
        }

        removed_option_ids = set(existing_options) - updated_option_ids

        if removed_option_ids:
            votes_count = self.session.scalar(
                select(func.count())
                .select_from(VoteSelectionModel)
                .where(
                    VoteSelectionModel.option_id.in_(removed_option_ids)
                )
            )

            if votes_count:
                raise ValueError(
                    "No se pueden eliminar opciones que ya tienen votos asociados."
                )

        poll_model.title = poll.title
        poll_model.description = poll.description
        poll_model.poll_type = poll.poll_type.value
        poll_model.max_selections = poll.max_selections
        poll_model.closes_at = poll.closes_at
        poll_model.is_active = poll.is_active

        updated_options = []

        for option in poll.options:
            existing_option = existing_options.get(option.id)

            if existing_option is not None:
                existing_option.text = option.text
                updated_options.append(existing_option)
            else:
                updated_options.append(
                    OptionModel(
                        id=option.id,
                        text=option.text
                    )
                )

        poll_model.options = updated_options

        self._commit()

    def save_poll(self, poll: Poll) -> None:
        """Persist a new poll and its options."""
        poll_model = poll_to_model(poll)
        self.session.add(poll_model)
        self._commit()

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Retrieve a poll's votes with their selections in order."""
        statement = (
            select(VoteModel)
            .options(selectinload(VoteModel.selections))
            .where(VoteModel.poll_id == poll_id)
        )

        vote_models = self.session.execute(statement).scalars().all()

        return [
            vote_to_entity(vote_model)
            for vote_model in vote_models
        ]
