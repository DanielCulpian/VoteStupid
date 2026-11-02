from uuid import UUID

import pytest

from app.application.use_cases.get_poll_results import GetPollResults
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.entities.vote import Vote
from app.domain.repositories.poll_repository import PollRepository


class FakePollRepository(PollRepository):

    def __init__(self, poll=None, votes=None):
        self.poll = poll
        self.votes = votes or []

    def get_by_id(self, poll_id: UUID):
        if self.poll and self.poll.id == poll_id:
            return self.poll
        return None

    def get_vote_by_voter(self, poll_id: UUID, voter_token_hash: str):
        return None

    def save_vote(self, vote: Vote) -> None:
        pass

    def update_vote(self, vote: Vote) -> None:
        pass

    def get_options_by_ids(
        self,
        poll_id: UUID,
        option_ids: list[UUID]
    ) -> list[UUID]:
        return []

    def update_poll(self, poll: Poll) -> None:
        pass

    def save_poll(self, poll: Poll) -> None:
        pass

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        return self.votes


def create_poll(poll_type: PollType, options: list[Option]) -> Poll:
    return Poll(
        title="Votación de prueba",
        poll_type=poll_type,
        options=options,
    )


def create_vote(poll: Poll, selected_options: list[Option], token: str) -> Vote:
    return Vote(
        poll_id=poll.id,
        voter_token_hash=token,
        selected_option_ids=[option.id for option in selected_options],
    )


def test_get_results_for_single_choice():
    options = [Option("A"), Option("B"), Option("C")]
    poll = create_poll(PollType.SINGLE_CHOICE, options)

    votes = [
        create_vote(poll, [options[0]], "token-1"),
        create_vote(poll, [options[0]], "token-2"),
        create_vote(poll, [options[1]], "token-3"),
    ]

    use_case = GetPollResults(FakePollRepository(poll, votes))

    results = use_case.execute(poll.id)

    assert results.total_votes == 3
    assert results.results[0].votes == 2
    assert results.results[0].points == 2
    assert results.results[0].percentage == pytest.approx(66.67, abs=0.01)
    assert results.results[1].votes == 1
    assert results.results[1].percentage == pytest.approx(33.33, abs=0.01)
    assert results.results[2].votes == 0
    assert results.results[2].percentage == 0


def test_get_results_for_multiple_choice():
    options = [Option("A"), Option("B"), Option("C")]
    poll = create_poll(PollType.MULTIPLE_CHOICE, options)

    votes = [
        create_vote(poll, [options[0], options[1]], "token-1"),
        create_vote(poll, [options[0], options[2]], "token-2"),
    ]

    use_case = GetPollResults(FakePollRepository(poll, votes))

    results = use_case.execute(poll.id)

    assert results.total_votes == 2
    assert results.results[0].votes == 2
    assert results.results[0].percentage == 100
    assert results.results[1].votes == 1
    assert results.results[1].percentage == 50
    assert results.results[2].votes == 1
    assert results.results[2].percentage == 50


def test_get_results_for_ranking():
    options = [Option("A"), Option("B"), Option("C")]
    poll = create_poll(PollType.RANKING, options)

    votes = [
        create_vote(poll, [options[0], options[1], options[2]], "token-1"),
        create_vote(poll, [options[1], options[2], options[0]], "token-2"),
    ]

    use_case = GetPollResults(FakePollRepository(poll, votes))

    results = use_case.execute(poll.id)

    assert results.total_votes == 2

    assert results.results[0].points == 2
    assert results.results[0].percentage == pytest.approx(33.33, abs=0.01)

    assert results.results[1].points == 3
    assert results.results[1].percentage == 50

    assert results.results[2].points == 1
    assert results.results[2].percentage == pytest.approx(16.67, abs=0.01)


def test_get_results_without_votes():
    options = [Option("A"), Option("B")]
    poll = create_poll(PollType.SINGLE_CHOICE, options)

    use_case = GetPollResults(FakePollRepository(poll))

    results = use_case.execute(poll.id)

    assert results.total_votes == 0

    for result in results.results:
        assert result.votes == 0
        assert result.points == 0
        assert result.percentage == 0


def test_get_results_for_nonexistent_poll():
    repository = FakePollRepository()
    use_case = GetPollResults(repository)

    results = use_case.execute(UUID(int=1))

    assert results is None