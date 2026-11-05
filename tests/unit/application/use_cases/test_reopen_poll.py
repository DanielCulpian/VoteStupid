
import pytest
from uuid import uuid4,UUID

from app.domain.entities.vote import Vote
from app.application.use_cases.reopen_poll import ReopenPoll
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


class FakePollRepository(PollRepository):

    def __init__(self):
        """Initialize the test repository's in-memory storage."""
        self.polls = {}

    def get_by_id(self, poll_id):
        """Find the poll in the mock repository."""
        return self.polls.get(poll_id)

    def update_poll(self, poll):
        """Replace the poll stored in the mock repository."""
        self.polls[poll.id] = poll

    def get_vote_by_voter(self, poll_id, voter_token_hash):
        """Indicate that this operation is not implemented in the test repository."""
        raise NotImplementedError

    def save_vote(self, vote):
        """Indicate that this operation is not implemented in the test repository."""
        raise NotImplementedError

    def update_vote(self, vote):
        """Indicate that this operation is not implemented in the test repository."""
        raise NotImplementedError

    def get_options_by_ids(self, poll_id, option_ids):
        """Indicate that this operation is not implemented in the test repository."""
        raise NotImplementedError

    def save_poll(self, poll):
        """Save the poll in the mock repository."""
        self.polls[poll.id] = poll

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Simulate an empty query result for this test scenario."""
        return []


def create_poll(is_active=False):
    """Build a poll and its options for the test scenario."""
    options = [
        Option(text="Opción 1"),
        Option(text="Opción 2")
    ]

    return Poll(
        title="Votación de prueba",
        poll_type=PollType.SINGLE_CHOICE,
        options=options,
        is_active=is_active
    )


def create_use_case(repository):
    """Build the test use case with the supplied repository."""
    return ReopenPoll(poll_repository=repository)


# 1. Reopen a poll successfully

def test_reopen_poll_successfully():
    """Verify reopen poll successfully."""
    poll = create_poll()
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    reopened_poll = use_case.execute(poll.id)

    assert reopened_poll.is_active is True
    assert reopened_poll.id == poll.id


# 2. Reject a nonexistent poll

def test_reopen_poll_rejects_nonexistent_poll():
    """Verify reopen poll rejects nonexistent poll."""
    repository = FakePollRepository()
    use_case = create_use_case(repository)

    with pytest.raises(ValueError, match="La votación no existe"):
        use_case.execute(uuid4())


# 3. Allow reopening an already open poll

def test_reopen_poll_allows_already_open_poll():
    """Verify reopen poll allows already open poll."""
    poll = create_poll(is_active=True)
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    reopened_poll = use_case.execute(poll.id)

    assert reopened_poll.is_active is True


# 4. Persist the updated state in the repository

def test_reopen_poll_persists_updated_poll():
    """Verify reopen poll persists updated poll."""
    poll = create_poll()
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    use_case.execute(poll.id)

    stored_poll = repository.get_by_id(poll.id)

    assert stored_poll.is_active is True
