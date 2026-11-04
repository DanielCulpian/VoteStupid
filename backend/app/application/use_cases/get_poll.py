from uuid import UUID

from app.domain.entities.poll import Poll
from app.domain.repositories.poll_repository import PollRepository


class GetPoll:

    def __init__(self, poll_repository: PollRepository):
        """Recibe las dependencias necesarias para ejecutar el caso de uso."""
        self.poll_repository = poll_repository

    def execute(self, poll_id: UUID) -> Poll | None:
        """Busca una votación por su identificador en el repositorio."""
        return self.poll_repository.get_by_id(poll_id)