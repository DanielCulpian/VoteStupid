import pytest

from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType

from app.infrastructure.repositories.sqlalchemy_poll_repository import (
    SqlAlchemyPollRepository
)

from app.domain.entities.vote import Vote
from uuid import uuid4

def test_save_and_get_poll(db_session):
    """Comprueba que SQLAlchemy guarda y recupera una votación con sus opciones."""
    # Arrange: preparamos una votación.
    poll = Poll(
        title="¿Qué película vemos?",
        description="Votación del sábado",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Matrix"),
            Option(text="Interestelar")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)

    # Act: guardamos y recuperamos la votación.
    repository.save_poll(poll)
    result = repository.get_by_id(poll.id)

    # Assert: comprobamos los datos recuperados.
    assert result is not None
    assert result.id == poll.id
    assert result.title == "¿Qué película vemos?"
    assert result.description == "Votación del sábado"
    assert result.poll_type == PollType.SINGLE_CHOICE
    assert result.is_active is True

    assert len(result.options) == 2
    assert result.options[0].text == "Matrix"
    assert result.options[1].text == "Interestelar"

def test_save_and_get_vote(db_session):
    """Comprueba que SQLAlchemy guarda y recupera un voto con sus selecciones."""
    poll = Poll(
        title="¿Qué película vemos?",
        poll_type=PollType.RANKING,
        options=[
            Option(text="Matrix"),
            Option(text="Interestelar"),
            Option(text="Origen")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    vote = Vote(
        poll_id=poll.id,
        voter_token_hash="hash_votante_001",
        selected_option_ids=[
            poll.options[1].id,
            poll.options[0].id,
            poll.options[2].id
        ]
    )

    repository.save_vote(vote)

    result = repository.get_vote_by_voter(
        poll.id,
        "hash_votante_001"
    )

    assert result is not None
    assert result.id == vote.id
    assert result.poll_id == poll.id
    assert result.voter_token_hash == "hash_votante_001"
    assert result.selected_option_ids == [
        poll.options[1].id,
        poll.options[0].id,
        poll.options[2].id
    ]

def test_update_vote(db_session):
    """Comprueba que SQLAlchemy sustituye las selecciones y conserva la identidad del voto."""
    poll = Poll(
        title="¿Qué película vemos?",
        poll_type=PollType.RANKING,
        options=[
            Option(text="Matrix"),
            Option(text="Interestelar"),
            Option(text="Origen")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    vote = Vote(
        poll_id=poll.id,
        voter_token_hash="hash_votante_002",
        selected_option_ids=[
            poll.options[0].id,
            poll.options[1].id,
            poll.options[2].id
        ]
    )

    repository.save_vote(vote)

    new_selection = [
        poll.options[2].id,
        poll.options[1].id,
        poll.options[0].id
    ]

    vote.update_selection(new_selection)
    repository.update_vote(vote)

    result = repository.get_vote_by_voter(
        poll.id,
        "hash_votante_002"
    )

    assert result is not None
    assert result.id == vote.id
    assert result.selected_option_ids == new_selection

def test_update_poll(db_session):
    """Comprueba que SQLAlchemy guarda los cambios de la votación."""
    poll = Poll(
        title="Votación original",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    poll.title = "Votación modificada"
    poll.options[0].text = "Opción modificada"

    repository.update_poll(poll)

    result = repository.get_by_id(poll.id)

    assert result is not None
    assert result.title == "Votación modificada"
    assert result.options[0].text == "Opción modificada"

def test_get_options_by_ids(db_session):
    """Comprueba que el repositorio filtra las opciones de la votación y conserva su orden."""
    poll = Poll(
        title="Votación de prueba",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    unknown_option_id = uuid4()

    result = repository.get_options_by_ids(
        poll.id,
        [
            poll.options[0].id,
            unknown_option_id,
            poll.options[1].id
        ]
    )

    assert result == [
        poll.options[0].id,
        poll.options[1].id
    ]

def test_get_vote_by_voter_returns_none_when_not_found(db_session):
    """Comprueba que la búsqueda del voto del participante devuelve None cuando no encuentra el voto."""
    repository = SqlAlchemyPollRepository(db_session)

    result = repository.get_vote_by_voter(
        uuid4(),
        "hash_inexistente"
    )

    assert result is None

def test_update_poll_rejects_removing_option_with_votes(db_session):
    """Comprueba que la actualización de votaciones impide eliminar una opción con votos asociados."""
    poll = Poll(
        title="Votación histórica",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    vote = Vote(
        poll_id=poll.id,
        voter_token_hash="hash_historico",
        selected_option_ids=[poll.options[0].id]
    )

    repository.save_vote(vote)

    updated_poll = repository.get_by_id(poll.id)

    updated_poll.options = [
        updated_poll.options[1]
    ]

    with pytest.raises(ValueError, match="No se pueden eliminar opciones"):
        repository.update_poll(updated_poll)

    # El voto histórico debe seguir existiendo.
    result = repository.get_vote_by_voter(
        poll.id,
        "hash_historico"
    )

    assert result is not None
    assert result.selected_option_ids == [poll.options[0].id]

def test_get_votes_by_poll_returns_empty_list_when_no_votes(db_session):
    """Comprueba que la consulta de votos de una votación devuelve una lista vacía si no hay votos."""
    poll = Poll(
        title="Votación sin participantes",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    result = repository.get_votes_by_poll(poll.id)

    assert result == []


def test_get_votes_by_poll_returns_all_votes(db_session):
    """Comprueba que la consulta de votos de una votación devuelve todos los votos asociados."""
    poll = Poll(
        title="¿Qué película vemos?",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Matrix"),
            Option(text="Interestelar"),
            Option(text="Origen")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    vote_1 = Vote(
        poll_id=poll.id,
        voter_token_hash="hash_participante_001",
        selected_option_ids=[poll.options[0].id]
    )

    vote_2 = Vote(
        poll_id=poll.id,
        voter_token_hash="hash_participante_002",
        selected_option_ids=[poll.options[1].id]
    )

    repository.save_vote(vote_1)
    repository.save_vote(vote_2)

    result = repository.get_votes_by_poll(poll.id)

    assert len(result) == 2

    result_by_hash = {
        vote.voter_token_hash: vote
        for vote in result
    }

    assert result_by_hash["hash_participante_001"].selected_option_ids == [
        poll.options[0].id
    ]

    assert result_by_hash["hash_participante_002"].selected_option_ids == [
        poll.options[1].id
    ]


def test_get_votes_by_poll_preserves_ranking_order(db_session):
    """Comprueba que la consulta de votos de una votación conserva el orden de las opciones del ranking."""
    poll = Poll(
        title="Ordena tus películas favoritas",
        poll_type=PollType.RANKING,
        options=[
            Option(text="Matrix"),
            Option(text="Interestelar"),
            Option(text="Origen")
        ]
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    ranking = [
        poll.options[2].id,
        poll.options[0].id,
        poll.options[1].id
    ]

    vote = Vote(
        poll_id=poll.id,
        voter_token_hash="hash_ranking_001",
        selected_option_ids=ranking
    )

    repository.save_vote(vote)

    result = repository.get_votes_by_poll(poll.id)

    assert len(result) == 1
    assert result[0].selected_option_ids == ranking