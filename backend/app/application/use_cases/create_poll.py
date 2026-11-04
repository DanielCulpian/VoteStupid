from datetime import datetime

from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository

from app.application.results.created_poll import CreatedPoll
from app.infrastructure.security.admin_token import (
    generate_admin_token,
    hash_admin_token,
)


class CreatePoll:

    def __init__(self, poll_repository: PollRepository):
        """Recibe las dependencias necesarias para ejecutar el caso de uso."""
        self.poll_repository = poll_repository

    def execute(
        self,
        title: str,
        option_texts: list[str],
        poll_type: PollType,
        description: str | None = None,
        max_selections: int | None = None,
        closes_at: datetime | None = None
    ) -> CreatedPoll:
        """Crea y guarda la votación y devuelve su token privado de administración."""

        # 1. Generar el secreto de administración.
        admin_token = generate_admin_token()

        # 2. Crear las opciones.
        options = [
            Option(text=option_text)
            for option_text in option_texts
        ]

        # 3. Crear la votación con el hash del secreto.
        poll = Poll(
            title=title,
            poll_type=poll_type,
            options=options,
            description=description,
            max_selections=max_selections,
            closes_at=closes_at,
            admin_token_hash=hash_admin_token(admin_token),
        )

        # 4. Guardar la votación.
        self.poll_repository.save_poll(poll)

        # 5. Devolver la votación y el secreto original.
        return CreatedPoll(
            poll=poll,
            admin_token=admin_token,
        )