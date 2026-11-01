from datetime import datetime

from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


class CreatePoll:

    def __init__(self, poll_repository: PollRepository):
        self.poll_repository = poll_repository

    def execute(
        self,
        title: str,
        option_texts: list[str],
        poll_type: PollType,
        description: str | None = None,
        max_selections: int | None = None,
        closes_at: datetime | None = None
    ) -> Poll:

        # 1. Crear las opciones
        options = [
            Option(text=option_text)
            for option_text in option_texts
        ]

        # 2. Crear la votación
        poll = Poll(
            title=title,
            poll_type=poll_type,
            options=options,
            description=description,
            max_selections=max_selections,
            closes_at=closes_at
        )

        # 3. Guardar la votación
        self.poll_repository.save_poll(poll)

        # 4. Devolver la votación
        return poll