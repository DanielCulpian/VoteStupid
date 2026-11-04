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
        """Filtra y ordena primero abiertas y después recientes, considerando el cierre programado."""
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
        """Asocia el repositorio a la sesión SQLAlchemy recibida."""
        self.session = session

    def _commit(self) -> None:
        """Confirma la transacción y la revierte si se produce un error."""
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_by_id(self, poll_id: UUID) -> Poll | None:
        """Obtiene una votación por su identificador o devuelve None si no existe."""
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
        """Busca el voto de un participante mediante la votación y el hash de su token."""
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
        """Guarda el voto y convierte un duplicado concurrente en un conflicto de participación."""
        vote_model = vote_to_model(vote)
        self.session.add(vote_model)
        try:
            self._commit()
        except IntegrityError as error:
            if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "uq_vote_poll_voter":
                raise VoteRuleError("Este participante ya ha votado.") from error
            raise

    def update_vote(self, vote: Vote) -> None:
        """Sustituye las selecciones del voto existente y guarda su fecha de modificación."""
        statement = (
            select(VoteModel)
            .options(selectinload(VoteModel.selections))
            .where(VoteModel.id == vote.id)
        )

        vote_model = self.session.execute(statement).scalar_one_or_none()

        if vote_model is None:
            raise ValueError("El voto que se intenta actualizar no existe.")

        # Eliminamos las selecciones anteriores y guardamos ese cambio.
        vote_model.selections.clear()
        self.session.flush()

        # Creamos las nuevas selecciones sobre el voto existente.
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
        """Devuelve los identificadores solicitados que pertenecen a la votación, en su orden."""
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
        """Actualiza la votación y sus opciones sin eliminar opciones que tengan votos."""
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
        """Guarda una nueva votación con sus opciones."""
        poll_model = poll_to_model(poll)
        self.session.add(poll_model)
        self._commit()

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Obtiene los votos de una votación con sus selecciones ordenadas."""
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
