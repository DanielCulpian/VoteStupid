from uuid import UUID

from app.domain.entities.poll import Poll
from app.domain.repositories.poll_repository import PollRepository


class ReopenPoll:

    def __init__(self, poll_repository: PollRepository):
        """Recibe las dependencias necesarias para ejecutar el caso de uso."""
        self.poll_repository = poll_repository

    def execute(self, poll_id: UUID) -> Poll:
        """Marca la votación como abierta y guarda el cambio."""

        # 1. Buscar la votación
        poll = self.poll_repository.get_by_id(poll_id)

        # 2. Comprobar si existe
        if poll is None:
            raise ValueError("La votación no existe.")

        # 3. Reabrir la votación
        poll.is_active = True

        # 4. Guardar los cambios
        self.poll_repository.update_poll(poll)

        # 5. Devolver la votación
        return poll
