
from uuid import UUID
from datetime import datetime, timezone

from app.domain.entities.vote import Vote
from app.domain.repositories.poll_repository import PollRepository
from app.application.use_cases.validate_vote_selection import (
    ValidateVoteSelection
)


class CastVote:

    def __init__(
        self,
        poll_repository: PollRepository,
        validate_vote_selection: ValidateVoteSelection
    ):
        self.poll_repository = poll_repository
        self.validate_vote_selection = validate_vote_selection

    def execute(
        self,
        poll_id: UUID,
        voter_token_hash: str,
        selected_option_ids: list[UUID]
    ) -> Vote:

        # 1. Obtener la votación
        poll = self.poll_repository.get_by_id(poll_id)

        if poll is None:
            raise ValueError("La votación no existe.")

        # 2. Comprobar que está abierta
        if not poll.is_active:
            raise ValueError("La votación está cerrada.")

        # 2.1 Comprobar que no ha alcanzado su fecha de cierre
        if (
            poll.closes_at is not None
            and datetime.now(timezone.utc) >= poll.closes_at
        ):
            raise ValueError("La votación ha alcanzado su fecha de cierre.")

        # 3. Comprobar que el participante no ha votado ya
        existing_vote = self.poll_repository.get_vote_by_voter(
            poll_id,
            voter_token_hash
        )

        if existing_vote is not None:
            raise ValueError("Este participante ya ha votado.")

        # 4. Validar la selección
        self.validate_vote_selection.execute(
            poll=poll,
            selected_option_ids=selected_option_ids
        )

        # 5. Crear el voto
        vote = Vote(
            poll_id=poll_id,
            voter_token_hash=voter_token_hash,
            selected_option_ids=selected_option_ids
        )

        # 6. Guardar el voto
        self.poll_repository.save_vote(vote)

        # 7. Devolver el voto creado
        return vote
