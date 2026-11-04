import pytest
from uuid import uuid4

from app.domain.entities.vote import Vote


def test_create_valid_vote():
    """Comprueba la creación de un voto con datos válidos."""
    poll_id = uuid4()
    option_ids = [uuid4(), uuid4()]

    vote = Vote(
        poll_id=poll_id,
        voter_token_hash="anonymous_hash_123",
        selected_option_ids=option_ids
    )

    assert vote.poll_id == poll_id
    assert vote.voter_token_hash == "anonymous_hash_123"
    assert vote.selected_option_ids == option_ids
    assert vote.id is not None
    assert vote.created_at is not None
    assert vote.updated_at is not None


def test_vote_rejects_empty_voter_token_hash():
    """Comprueba que el voto rechaza un hash de participante vacío."""
    with pytest.raises(ValueError):
        Vote(
            poll_id=uuid4(),
            voter_token_hash="   ",
            selected_option_ids=[uuid4()]
        )


def test_vote_requires_at_least_one_option():
    """Comprueba que el voto exige al menos una opción."""
    with pytest.raises(ValueError):
        Vote(
            poll_id=uuid4(),
            voter_token_hash="anonymous_hash_123",
            selected_option_ids=[]
        )


def test_vote_rejects_duplicate_options():
    """Comprueba que el voto rechaza opciones repetidas."""
    option_id = uuid4()

    with pytest.raises(ValueError):
        Vote(
            poll_id=uuid4(),
            voter_token_hash="anonymous_hash_123",
            selected_option_ids=[option_id, option_id]
        )

def test_update_vote_selection():
    """Comprueba que cambiar la selección actualiza las opciones y la fecha del voto."""
    vote = Vote(
        poll_id=uuid4(),
        voter_token_hash="anonymous_hash_123",
        selected_option_ids=[uuid4()]
    )

    new_selection = [uuid4(), uuid4()]
    original_id = vote.id
    original_created_at = vote.created_at

    vote.update_selection(new_selection)

    assert vote.selected_option_ids == new_selection
    assert vote.id == original_id
    assert vote.created_at == original_created_at
    assert vote.updated_at >= original_created_at


def test_update_vote_rejects_empty_selection():
    """Comprueba que la actualización de votos rechaza una selección vacía."""
    vote = Vote(
        poll_id=uuid4(),
        voter_token_hash="anonymous_hash_123",
        selected_option_ids=[uuid4()]
    )

    with pytest.raises(ValueError):
        vote.update_selection([])


def test_update_vote_rejects_duplicate_options():
    """Comprueba que la actualización de votos rechaza opciones repetidas."""
    vote = Vote(
        poll_id=uuid4(),
        voter_token_hash="anonymous_hash_123",
        selected_option_ids=[uuid4()]
    )

    option_id = uuid4()

    with pytest.raises(ValueError):
        vote.update_selection([option_id, option_id])