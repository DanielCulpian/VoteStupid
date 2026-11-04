
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
        """Inicializa el almacenamiento en memoria del repositorio de prueba."""
        self.polls = {}

    def get_by_id(self, poll_id):
        """Busca la votación en el repositorio simulado."""
        return self.polls.get(poll_id)

    def update_poll(self, poll):
        """Sustituye la votación almacenada en el repositorio simulado."""
        self.polls[poll.id] = poll

    def get_vote_by_voter(self, poll_id, voter_token_hash):
        """Señala que esta operación no está implementada en el repositorio de prueba."""
        raise NotImplementedError

    def save_vote(self, vote):
        """Señala que esta operación no está implementada en el repositorio de prueba."""
        raise NotImplementedError

    def update_vote(self, vote):
        """Señala que esta operación no está implementada en el repositorio de prueba."""
        raise NotImplementedError

    def get_options_by_ids(self, poll_id, option_ids):
        """Señala que esta operación no está implementada en el repositorio de prueba."""
        raise NotImplementedError

    def save_poll(self, poll):
        """Guarda la votación en el repositorio simulado."""
        self.polls[poll.id] = poll

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Simula una consulta sin resultados para este escenario de prueba."""
        return []


def create_poll(is_active=False):
    """Construye una votación y sus opciones para preparar el escenario de prueba."""
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
    """Construye el caso de uso de la prueba con el repositorio indicado."""
    return ReopenPoll(poll_repository=repository)


# 1. Reabrir una votación correctamente

def test_reopen_poll_successfully():
    """Comprueba que la reapertura de votaciones se completa correctamente."""
    poll = create_poll()
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    reopened_poll = use_case.execute(poll.id)

    assert reopened_poll.is_active is True
    assert reopened_poll.id == poll.id


# 2. Rechazar una votación inexistente

def test_reopen_poll_rejects_nonexistent_poll():
    """Comprueba que la reapertura de votaciones rechaza una votación inexistente."""
    repository = FakePollRepository()
    use_case = create_use_case(repository)

    with pytest.raises(ValueError, match="La votación no existe"):
        use_case.execute(uuid4())


# 3. Permitir reabrir una votación que ya está abierta

def test_reopen_poll_allows_already_open_poll():
    """Comprueba que la reapertura de votaciones permite reabrir una votación que ya estaba abierta."""
    poll = create_poll(is_active=True)
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    reopened_poll = use_case.execute(poll.id)

    assert reopened_poll.is_active is True


# 4. Persistir el estado actualizado en el repositorio

def test_reopen_poll_persists_updated_poll():
    """Comprueba que la reapertura de votaciones guarda el nuevo estado de la votación."""
    poll = create_poll()
    repository = FakePollRepository()
    repository.polls[poll.id] = poll

    use_case = create_use_case(repository)

    use_case.execute(poll.id)

    stored_poll = repository.get_by_id(poll.id)

    assert stored_poll.is_active is True
