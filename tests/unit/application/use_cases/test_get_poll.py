from unittest.mock import create_autospec
from uuid import uuid4

from app.application.use_cases.get_poll import GetPoll
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


def test_get_poll_returns_poll_when_it_exists():
    """Verify get poll returns poll when it exists."""
    # Arrange: prepare a poll and a mock repository.
    poll_id = uuid4()

    poll = Poll(
        title="¿Cuál es la mejor opción?",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B")
        ]
    )

    repository = create_autospec(PollRepository, instance=True)
    repository.get_by_id.return_value = poll

    use_case = GetPoll(repository)

    # Act: execute the use case.
    result = use_case.execute(poll_id)

    # Assert: check the result and repository call.
    assert result is poll
    repository.get_by_id.assert_called_once_with(poll_id)


def test_get_poll_returns_none_when_poll_does_not_exist():
    """Verify get poll returns none when poll does not exist."""
    # Arrange: simulate a repository that cannot find the poll.
    poll_id = uuid4()

    repository = create_autospec(PollRepository, instance=True)
    repository.get_by_id.return_value = None

    use_case = GetPoll(repository)

    # Act: execute the use case.
    result = use_case.execute(poll_id)

    # Assert: verify that the result is None.
    assert result is None
    repository.get_by_id.assert_called_once_with(poll_id)