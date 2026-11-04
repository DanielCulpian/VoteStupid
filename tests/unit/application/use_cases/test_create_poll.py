import pytest
from uuid import UUID
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository
from app.application.use_cases.create_poll import CreatePoll
from app.domain.entities.vote import Vote


class FakePollRepository(PollRepository):

    def __init__(self):
        """Inicializa el almacenamiento en memoria del repositorio de prueba."""
        self.polls = {}

    def save_poll(self, poll):
        """Guarda la votación en el repositorio simulado."""
        self.polls[poll.id] = poll

    def get_by_id(self, poll_id):
        """Busca la votación en el repositorio simulado."""
        return self.polls.get(poll_id)

    def update_poll(self, poll):
        """Señala que esta operación no está implementada en el repositorio de prueba."""
        raise NotImplementedError

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

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Simula una consulta sin resultados para este escenario de prueba."""
        return []


def test_create_poll_successfully():
    """Comprueba que la creación de votaciones se completa correctamente."""
    repository = FakePollRepository()
    use_case = CreatePoll(repository)

    result = use_case.execute(
        title="¿Qué hacemos el sábado?",
        option_texts=["Ir al cine", "Ir a cenar"],
        poll_type=PollType.SINGLE_CHOICE
    )

    poll = result.poll

    assert poll.title == "¿Qué hacemos el sábado?"
    assert len(poll.options) == 2
    assert poll.poll_type == PollType.SINGLE_CHOICE
    assert repository.get_by_id(poll.id) == poll
    assert poll.admin_token_hash is not None
    assert len(poll.admin_token_hash) == 64
    assert result.admin_token


def test_create_poll_with_optional_fields():
    """Comprueba que la creación de votaciones conserva los campos opcionales indicados."""
    repository = FakePollRepository()
    use_case = CreatePoll(repository)

    result = use_case.execute(
        title="¿Qué hacemos?",
        option_texts=["Cine", "Cena"],
        poll_type=PollType.MULTIPLE_CHOICE,
        description="Votación del sábado",
        max_selections=2
    )

    poll = result.poll

    assert poll.description == "Votación del sábado"
    assert poll.max_selections == 2
    assert poll.admin_token_hash is not None
    assert result.admin_token


def test_create_poll_rejects_empty_title():
    """Comprueba que la creación de votaciones rechaza un título vacío."""
    repository = FakePollRepository()
    use_case = CreatePoll(repository)

    with pytest.raises(ValueError):
        use_case.execute(
            title="",
            option_texts=["Cine", "Cena"],
            poll_type=PollType.SINGLE_CHOICE
        )


def test_create_poll_requires_at_least_two_options():
    """Comprueba que la creación de votaciones exige al menos dos opciones."""
    repository = FakePollRepository()
    use_case = CreatePoll(repository)

    with pytest.raises(ValueError):
        use_case.execute(
            title="¿Qué hacemos?",
            option_texts=["Cine"],
            poll_type=PollType.SINGLE_CHOICE
        )
