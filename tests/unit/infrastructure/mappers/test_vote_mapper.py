from app.domain.entities.vote import Vote
from app.infrastructure.mappers.vote_mapper import to_model, to_entity


def test_to_model_converts_vote_and_selections():
    """Verify to model converts vote and selections."""
    from uuid import uuid4

    poll_id = uuid4()
    option_1_id = uuid4()
    option_2_id = uuid4()

    vote = Vote(
        poll_id=poll_id,
        voter_token_hash="hash_de_prueba",
        selected_option_ids=[option_2_id, option_1_id]
    )

    result = to_model(vote)

    assert result.id == vote.id
    assert result.poll_id == poll_id
    assert result.voter_token_hash == "hash_de_prueba"
    assert len(result.selections) == 2
    assert result.selections[0].option_id == option_2_id
    assert result.selections[0].position == 0
    assert result.selections[1].option_id == option_1_id
    assert result.selections[1].position == 1


def test_to_entity_converts_vote_and_preserves_selection_order():
    """Verify to entity converts vote and preserves selection order."""
    from uuid import uuid4

    poll_id = uuid4()
    option_1_id = uuid4()
    option_2_id = uuid4()

    vote = Vote(
        poll_id=poll_id,
        voter_token_hash="hash_de_prueba",
        selected_option_ids=[option_2_id, option_1_id]
    )

    model = to_model(vote)
    result = to_entity(model)

    assert result.id == vote.id
    assert result.poll_id == poll_id
    assert result.voter_token_hash == vote.voter_token_hash
    assert result.selected_option_ids == [option_2_id, option_1_id]