
from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.poll import Poll
from app.domain.entities.vote import Vote


class PollRepository(ABC):

    @abstractmethod
    def get_by_id(self, poll_id: UUID) -> Poll | None:
        """Obtiene una votación por su identificador o devuelve None si no existe."""
        pass

    @abstractmethod
    def get_vote_by_voter(
        self,
        poll_id: UUID,
        voter_token_hash: str
    ) -> Vote | None:
        """Busca el voto de un participante mediante la votación y el hash de su token."""
        pass

    @abstractmethod
    def save_vote(self, vote: Vote) -> None:
        """Guarda un nuevo voto con sus opciones seleccionadas."""
        pass

    @abstractmethod
    def update_vote(self, vote: Vote) -> None:
        """Sustituye las selecciones del voto existente y guarda su fecha de modificación."""
        pass

    @abstractmethod
    def get_options_by_ids(
        self,
        poll_id: UUID,
        option_ids: list[UUID]
    ) -> list[UUID]:
        """Devuelve los identificadores solicitados que pertenecen a la votación, en su orden."""
        pass

    @abstractmethod
    def update_poll(self, poll: Poll) -> None:
        """Define la actualización de una votación en el repositorio."""
        pass

    @abstractmethod
    def save_poll(self, poll: Poll) -> None:
        """Guarda una nueva votación con sus opciones."""
        pass

    @abstractmethod
    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Obtiene los votos de una votación con sus selecciones ordenadas."""
        pass