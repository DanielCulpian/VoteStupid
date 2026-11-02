import pytest
from pydantic import ValidationError
from uuid import uuid4

from app.presentation.api.schemas import (
    CastVoteRequest,
    UpdateVoteRequest,
)


def test_cast_vote_request_accepts_valid_selection():
    option_id = uuid4()

    request = CastVoteRequest(
        selected_option_ids=[option_id]
    )

    assert request.selected_option_ids == [option_id]


def test_cast_vote_request_rejects_empty_selection():
    with pytest.raises(ValidationError):
        CastVoteRequest(selected_option_ids=[])


def test_update_vote_request_accepts_valid_selection():
    option_id = uuid4()

    request = UpdateVoteRequest(
        selected_option_ids=[option_id]
    )

    assert request.selected_option_ids == [option_id]


def test_update_vote_request_rejects_empty_selection():
    with pytest.raises(ValidationError):
        UpdateVoteRequest(selected_option_ids=[])