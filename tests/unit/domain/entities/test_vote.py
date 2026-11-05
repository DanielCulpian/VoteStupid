import pytest
from uuid import uuid4

from app.domain.entities.vote import Vote


def test_create_valid_vote():
    """Verify create valid vote."""
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
    """Verify vote rejects empty voter token hash."""
    with pytest.raises(ValueError):
        Vote(
            poll_id=uuid4(),
            voter_token_hash="   ",
            selected_option_ids=[uuid4()]
        )


def test_vote_requires_at_least_one_option():
    """Verify vote requires at least one option."""
    with pytest.raises(ValueError):
        Vote(
            poll_id=uuid4(),
            voter_token_hash="anonymous_hash_123",
            selected_option_ids=[]
        )


def test_vote_rejects_duplicate_options():
    """Verify vote rejects duplicate options."""
    option_id = uuid4()

    with pytest.raises(ValueError):
        Vote(
            poll_id=uuid4(),
            voter_token_hash="anonymous_hash_123",
            selected_option_ids=[option_id, option_id]
        )

def test_update_vote_selection():
    """Verify update vote selection."""
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
    """Verify update vote rejects empty selection."""
    vote = Vote(
        poll_id=uuid4(),
        voter_token_hash="anonymous_hash_123",
        selected_option_ids=[uuid4()]
    )

    with pytest.raises(ValueError):
        vote.update_selection([])


def test_update_vote_rejects_duplicate_options():
    """Verify update vote rejects duplicate options."""
    vote = Vote(
        poll_id=uuid4(),
        voter_token_hash="anonymous_hash_123",
        selected_option_ids=[uuid4()]
    )

    option_id = uuid4()

    with pytest.raises(ValueError):
        vote.update_selection([option_id, option_id])