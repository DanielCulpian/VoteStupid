from uuid import UUID

from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


class ValidateVoteSelection:

    def __init__(self, poll_repository: PollRepository):
        self.poll_repository = poll_repository

    def execute(
        self,
        poll: Poll,
        selected_option_ids: list[UUID]
    ) -> None:

        # 1. Comprobar que se ha seleccionado alguna opción
        if not selected_option_ids:
            raise ValueError("Debes seleccionar al menos una opción.")

        # 2. Comprobar que no hay opciones duplicadas
        if len(selected_option_ids) != len(set(selected_option_ids)):
            raise ValueError("No puedes seleccionar una opción varias veces.")

        # 3. Comprobar que las opciones pertenecen a la votación
        valid_option_ids = self.poll_repository.get_options_by_ids(
            poll.id,
            selected_option_ids
        )

        if set(valid_option_ids) != set(selected_option_ids):
            raise ValueError(
                "Una o varias opciones no pertenecen a esta votación."
            )

        # 4. Validar según el tipo de votación
        if poll.poll_type == PollType.SINGLE_CHOICE:
            if len(selected_option_ids) != 1:
                raise ValueError(
                    "En una votación de elección única debes seleccionar "
                    "exactamente una opción."
                )

        elif poll.poll_type == PollType.MULTIPLE_CHOICE:
            if (
                poll.max_selections is not None
                and len(selected_option_ids) > poll.max_selections
            ):
                raise ValueError(
                    f"No puedes seleccionar más de {poll.max_selections} opciones."
                )

        elif poll.poll_type == PollType.RANKING:
            if len(selected_option_ids) != len(poll.options):
                raise ValueError(
                    "En una votación de ranking debes ordenar todas las opciones."
                )