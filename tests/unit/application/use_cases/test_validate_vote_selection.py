
import pytest
from uuid import UUID
from app.domain.entities.vote import Vote
from app.application.use_cases.validate_vote_selection import (
    ValidateVoteSelection
)
from app.domain.entities.poll import Poll
from app.domain.entities.option import Option
from app.domain.entities.poll_type import PollType


class FakePollRepository:

    def get_options_by_ids(self, poll_id, option_ids):
        """Simula la consulta de opciones que utiliza este escenario de validación."""
        return option_ids

    def save_poll(self, poll):
        """Guarda la votación en el repositorio simulado."""
        self.polls[poll.id] = poll

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Simula una consulta sin resultados para este escenario de prueba."""
        return []


def create_poll(poll_type, max_selections=None):
    """Construye una votación y sus opciones para preparar el escenario de prueba."""
    options = [
        Option(text="Opción A"),
        Option(text="Opción B"),
        Option(text="Opción C")
    ]

    poll = Poll(
        title="Votación de prueba",
        poll_type=poll_type,
        options=options,
        max_selections=max_selections
    )

    return poll, options


def test_validate_vote_selection_rejects_empty_selection():
    """Comprueba que la validación de selecciones rechaza una selección vacía."""
    poll, options = create_poll(PollType.SINGLE_CHOICE)

    validator = ValidateVoteSelection(FakePollRepository())

    with pytest.raises(
        ValueError,
        match="Debes seleccionar al menos una opción."
    ):
        validator.execute(
            poll=poll,
            selected_option_ids=[]
        )


def test_validate_vote_selection_rejects_duplicate_options():
    """Comprueba que la validación de selecciones rechaza opciones repetidas."""
    poll, options = create_poll(PollType.MULTIPLE_CHOICE)

    validator = ValidateVoteSelection(FakePollRepository())

    with pytest.raises(
        ValueError,
        match="No puedes seleccionar una opción varias veces."
    ):
        validator.execute(
            poll=poll,
            selected_option_ids=[
                options[0].id,
                options[0].id
            ]
        )


def test_validate_vote_selection_rejects_options_from_another_poll():
    """Comprueba que la validación de selecciones rechaza opciones de otra votación."""
    poll, options = create_poll(PollType.MULTIPLE_CHOICE)

    validator = ValidateVoteSelection(FakePollRepository())

    class FakeRepositoryWithInvalidOptions:
        def get_options_by_ids(self, poll_id, option_ids):
            """Simula la consulta de opciones que utiliza este escenario de validación."""
            return [options[0].id]

    validator = ValidateVoteSelection(FakeRepositoryWithInvalidOptions())

    with pytest.raises(
        ValueError,
        match="Una o varias opciones no pertenecen a esta votación."
    ):
        validator.execute(
            poll=poll,
            selected_option_ids=[
                options[0].id,
                options[1].id
            ]
        )


def test_validate_vote_selection_rejects_multiple_options_in_single_choice():
    """Comprueba que la validación de selecciones rechaza varias opciones en elección única."""
    poll, options = create_poll(PollType.SINGLE_CHOICE)

    validator = ValidateVoteSelection(FakePollRepository())

    with pytest.raises(
        ValueError,
        match="En una votación de elección única debes seleccionar exactamente una opción."
    ):
        validator.execute(
            poll=poll,
            selected_option_ids=[
                options[0].id,
                options[1].id
            ]
        )


def test_validate_vote_selection_rejects_exceeding_max_selections():
    """Comprueba que la validación de selecciones rechaza superar el máximo de selecciones."""
    poll, options = create_poll(
        PollType.MULTIPLE_CHOICE,
        max_selections=2
    )

    validator = ValidateVoteSelection(FakePollRepository())

    with pytest.raises(
        ValueError,
        match="No puedes seleccionar más de 2 opciones."
    ):
        validator.execute(
            poll=poll,
            selected_option_ids=[
                options[0].id,
                options[1].id,
                options[2].id
            ]
        )


def test_validate_vote_selection_allows_multiple_options_without_limit():
    """Comprueba que la validación de selecciones permite varias opciones cuando no se ha fijado un límite."""
    poll, options = create_poll(PollType.MULTIPLE_CHOICE)

    validator = ValidateVoteSelection(FakePollRepository())

    validator.execute(
        poll=poll,
        selected_option_ids=[
            options[0].id,
            options[1].id,
            options[2].id
        ]
    )


def test_validate_vote_selection_rejects_incomplete_ranking():
    """Comprueba que la validación de selecciones rechaza un ranking incompleto."""
    poll, options = create_poll(PollType.RANKING)

    validator = ValidateVoteSelection(FakePollRepository())

    with pytest.raises(
        ValueError,
        match="En una votación de ranking debes ordenar todas las opciones."
    ):
        validator.execute(
            poll=poll,
            selected_option_ids=[
                options[0].id,
                options[1].id
            ]
        )


def test_validate_vote_selection_accepts_complete_ranking():
    """Comprueba que la validación de selecciones acepta un ranking completo."""
    poll, options = create_poll(PollType.RANKING)

    validator = ValidateVoteSelection(FakePollRepository())

    validator.execute(
        poll=poll,
        selected_option_ids=[
            options[2].id,
            options[0].id,
            options[1].id
        ]
    )
