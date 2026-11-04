from app.domain.vote_rule_error import VoteRuleError

from uuid import UUID
from datetime import datetime, timezone

from app.domain.entities.vote import Vote
from app.domain.repositories.poll_repository import PollRepository
from app.application.use_cases.validate_vote_selection import (
    ValidateVoteSelection
)


class UpdateVote:

    def __init__(
        self,
        poll_repository: PollRepository,
        validate_vote_selection: ValidateVoteSelection
    ):
        """Recibe las dependencias necesarias para ejecutar el caso de uso."""
        self.poll_repository = poll_repository
        self.validate_vote_selection = validate_vote_selection

    def execute(
        self,
        poll_id: UUID,
        voter_token_hash: str,
        selected_option_ids: list[UUID]
    ) -> Vote:
        """Valida la votación y la selección antes de modificar el voto del participante."""

        # 1. Obtener la votación
        poll = self.poll_repository.get_by_id(poll_id)

        if poll is None:
            raise VoteRuleError("La votación no existe.")

        # 2. Comprobar que está abierta
        if not poll.is_active:
            raise VoteRuleError("La votación está cerrada.")

        # 3. Comprobar la fecha límite
        if (
            poll.closes_at is not None
            and datetime.now(timezone.utc) >= poll.closes_at
        ):
            raise VoteRuleError("La votación ha alcanzado su fecha de cierre.")

        # 4. Buscar el voto existente
        existing_vote = self.poll_repository.get_vote_by_voter(
            poll_id,
            voter_token_hash
        )

        if existing_vote is None:
            raise VoteRuleError("Este participante todavía no ha votado.")

        # 5. Validar la nueva selección
        self.validate_vote_selection.execute(
            poll=poll,
            selected_option_ids=selected_option_ids
        )

        # 6. Actualizar el voto
        existing_vote.update_selection(selected_option_ids)

        # 7. Guardar los cambios
        self.poll_repository.update_vote(existing_vote)

        # 8. Devolver el voto actualizado
        return existing_vote
