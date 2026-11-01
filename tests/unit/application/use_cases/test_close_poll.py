
import pytest
from uuid import uuid4

from app.application.use_cases.close_poll import ClosePoll
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


class FakePollRepository(PollRepository):

    def __init__(self):
        self.polls = {}

    def get_by_id(self, poll_id):
        return self.polls.get(poll_id)

    def update_poll(self, poll):
        self.polls[poll.id] = poll

    def get_vote_by_voter(self, poll_id, voter_token_hash):
        raise NotImplementedError

    def save_vote(self, vote):
        raise NotImplementedError

    def update_vote(self, vote):
        raise NotImplementedError

    def get_options_by_ids(self, poll_id, option_ids):
        raise NotImplementedError

    def save_poll(self, poll):
        self.polls[poll.id] = poll


def create_poll(is_active=True):
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
    return ClosePoll(poll_repository=repository)


# 1. Cerrar una votación correctamente

def test_close_poll_successfully():
    poll = create_poll()
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    closed_poll = use_case.execute(poll.id)

    assert closed_poll.is_active is False
    assert closed_poll.id == poll.id


# 2. Rechazar una votación inexistente

def test_close_poll_rejects_nonexistent_poll():
    repository = FakePollRepository()
    use_case = create_use_case(repository)

    with pytest.raises(ValueError, match="La votación no existe"):
        use_case.execute(uuid4())


# 3. Permitir cerrar una votación que ya está cerrada

def test_close_poll_allows_already_closed_poll():
    poll = create_poll(is_active=False)
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    closed_poll = use_case.execute(poll.id)

    assert closed_poll.is_active is False


# 4. Persistir el estado actualizado en el repositorio

def test_close_poll_persists_updated_poll():
    poll = create_poll()
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    use_case.execute(poll.id)

    stored_poll = repository.get_by_id(poll.id)

    assert stored_poll.is_active is False
