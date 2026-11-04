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
        """Inicializa el almacenamiento en memoria del repositorio de prueba."""
        self.poll = poll
        self.votes = votes or []

    def get_by_id(self, poll_id: UUID):
        """Busca la votación en el repositorio simulado."""
        if self.poll and self.poll.id == poll_id:
            return self.poll
        return None

    def get_vote_by_voter(self, poll_id: UUID, voter_token_hash: str):
        """Simula que no existe un voto del participante para este escenario de prueba."""
        return None

    def save_vote(self, vote: Vote) -> None:
        """Completa el contrato del repositorio sin realizar operaciones en este escenario de prueba."""
        pass

    def update_vote(self, vote: Vote) -> None:
        """Completa el contrato del repositorio sin realizar operaciones en este escenario de prueba."""
        pass

    def get_options_by_ids(
        self,
        poll_id: UUID,
        option_ids: list[UUID]
    ) -> list[UUID]:
        """Simula una consulta sin resultados para este escenario de prueba."""
        return []

    def update_poll(self, poll: Poll) -> None:
        """Completa el contrato del repositorio sin realizar operaciones en este escenario de prueba."""
        pass

    def save_poll(self, poll: Poll) -> None:
        """Completa el contrato del repositorio sin realizar operaciones en este escenario de prueba."""
        pass

    def get_votes_by_poll(self, poll_id: UUID) -> list[Vote]:
        """Devuelve los votos preparados para el escenario de resultados."""
        return self.votes


def create_poll(poll_type: PollType, options: list[Option]) -> Poll:
    """Construye una votación y sus opciones para preparar el escenario de prueba."""
    return Poll(
        title="Votación de prueba",
        poll_type=poll_type,
        options=options,
    )


def create_vote(poll: Poll, selected_options: list[Option], token: str) -> Vote:
    """Construye un voto de prueba con las selecciones indicadas."""
    return Vote(
        poll_id=poll.id,
        voter_token_hash=token,
        selected_option_ids=[option.id for option in selected_options],
    )


def test_get_results_for_single_choice():
    """Comprueba los votos y porcentajes de una votación de elección única."""
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
    """Comprueba los votos y porcentajes de una votación de elección múltiple."""
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
    """Comprueba los puntos y porcentajes de una votación por ranking."""
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
    """Comprueba que los resultados son cero cuando no hay votos."""
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
    """Comprueba que el cálculo devuelve None para una votación inexistente."""
    repository = FakePollRepository()
    use_case = GetPollResults(repository)

    results = use_case.execute(UUID(int=1))

    assert results is None