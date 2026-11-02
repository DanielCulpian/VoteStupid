
from uuid import UUID
from datetime import datetime, timezone

import pytest

from app.application.use_cases.cast_vote import CastVote
from app.application.use_cases.validate_vote_selection import (
    ValidateVoteSelection
)
from app.domain.entities.poll import Poll
from app.domain.entities.option import Option
from app.domain.entities.vote import Vote
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


class FakePollRepository:

    def __init__(self):
        self.polls = {}
        self.votes = []

    def get_by_id(self, poll_id):
        return self.polls.get(poll_id)

    def get_vote_by_voter(self, poll_id, voter_token_hash):
        for vote in self.votes:
            if (
                vote.poll_id == poll_id
                and vote.voter_token_hash == voter_token_hash
            ):
                return vote
        return None

    def get_options_by_ids(self, poll_id, option_ids):
        poll = self.get_by_id(poll_id)

        if poll is None:
            return []

        valid_ids = {option.id for option in poll.options}

        return [
            option_id
            for option_id in option_ids
            if option_id in valid_ids
        ]

    def save_vote(self, vote):
        self.votes.append(vote)

    def update_vote(self, vote: Vote) -> None:
        self.votes[(vote.poll_id, vote.voter_token_hash)] = vote

    def update_poll(self, poll: Poll) -> None:
        self.polls[poll.id] = poll

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


def create_use_case(repository):
    validator = ValidateVoteSelection(repository)

    return CastVote(
        poll_repository=repository,
        validate_vote_selection=validator
    )


def test_fake_repository_can_store_and_retrieve_poll():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)

    repository.polls[poll.id] = poll

    assert repository.get_by_id(poll.id) == poll


def test_cast_vote_successfully():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash="hash_participante_1",
        selected_option_ids=[options[0].id]
    )

    assert isinstance(vote, Vote)
    assert len(repository.votes) == 1
    assert repository.votes[0] == vote


def test_cast_vote_rejects_duplicate_voter():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    repository.polls[poll.id] = poll

    existing_vote = Vote(
        poll_id=poll.id,
        voter_token_hash="hash_participante_1",
        selected_option_ids=[options[0].id]
    )
    repository.votes.append(existing_vote)

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="Este participante ya ha votado."
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[options[1].id]
        )

    assert len(repository.votes) == 1


def test_cast_vote_rejects_closed_poll():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    poll.is_active = False
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    with pytest.raises(ValueError, match="La votación está cerrada."):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[options[0].id]
        )


def test_cast_vote_rejects_nonexistent_poll():
    repository = FakePollRepository()
    use_case = create_use_case(repository)

    with pytest.raises(ValueError, match="La votación no existe."):
        use_case.execute(
            poll_id=UUID(int=1),
            voter_token_hash="hash_participante_1",
            selected_option_ids=[UUID(int=2)]
        )


def test_cast_vote_rejects_empty_selection():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="Debes seleccionar al menos una opción."
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[]
        )


def test_cast_vote_rejects_options_from_another_poll():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    other_poll, other_options = create_poll(PollType.SINGLE_CHOICE)

    repository.polls[poll.id] = poll
    repository.polls[other_poll.id] = other_poll

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="Una o varias opciones no pertenecen a esta votación."
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[other_options[0].id]
        )


def test_cast_vote_rejects_multiple_options_in_single_choice():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="En una votación de elección única debes seleccionar"
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[
                options[0].id,
                options[1].id
            ]
        )


def test_cast_vote_rejects_exceeding_max_selections():
    repository = FakePollRepository()
    poll, options = create_poll(
        PollType.MULTIPLE_CHOICE,
        max_selections=2
    )
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="No puedes seleccionar más de 2 opciones."
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[
                options[0].id,
                options[1].id,
                options[2].id
            ]
        )


def test_cast_vote_allows_multiple_options_without_limit():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.MULTIPLE_CHOICE)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash="hash_participante_1",
        selected_option_ids=[
            options[0].id,
            options[1].id,
            options[2].id
        ]
    )

    assert len(vote.selected_option_ids) == 3


def test_cast_vote_rejects_incomplete_ranking():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.RANKING)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="En una votación de ranking debes ordenar todas las opciones."
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[
                options[0].id,
                options[1].id
            ]
        )


def test_cast_vote_accepts_complete_ranking():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.RANKING)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash="hash_participante_1",
        selected_option_ids=[
            options[2].id,
            options[0].id,
            options[1].id
        ]
    )

    assert len(vote.selected_option_ids) == 3


def test_cast_vote_rejects_duplicate_options():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.MULTIPLE_CHOICE)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="No puedes seleccionar una opción varias veces."
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[
                options[0].id,
                options[0].id
            ]
        )


def test_cast_vote_rejects_expired_poll():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    poll.closes_at = datetime.now(timezone.utc)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    with pytest.raises(
        ValueError,
        match="La votación ha alcanzado su fecha de cierre."
    ):
        use_case.execute(
            poll_id=poll.id,
            voter_token_hash="hash_participante_1",
            selected_option_ids=[options[0].id]
        )


def test_cast_vote_allows_vote_before_closing_date():
    repository = FakePollRepository()
    poll, options = create_poll(PollType.SINGLE_CHOICE)
    poll.closes_at = datetime.now(timezone.utc).replace(year=2099)
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    vote = use_case.execute(
        poll_id=poll.id,
        voter_token_hash="hash_participante_1",
        selected_option_ids=[options[0].id]
    )

    assert isinstance(vote, Vote)
    assert len(repository.votes) == 1
