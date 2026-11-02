
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
        return option_ids

    def save_poll(self, poll):
        self.polls[poll.id] = poll

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        return []


def create_poll(poll_type, max_selections=None):
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
    poll, options = create_poll(PollType.MULTIPLE_CHOICE)

    validator = ValidateVoteSelection(FakePollRepository())

    class FakeRepositoryWithInvalidOptions:
        def get_options_by_ids(self, poll_id, option_ids):
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
