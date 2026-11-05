import pytest
from pydantic import ValidationError

from app.domain.entities.poll_type import PollType
from app.presentation.api.schemas import CreatePollRequest


def valid_poll_data():
    """Provide valid poll creation data for schema tests."""
    return {
        "title": "Mi votación",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": PollType.SINGLE_CHOICE,
    }


def test_create_poll_request_accepts_valid_data():
    """Verify create poll request accepts valid data."""
    request = CreatePollRequest(**valid_poll_data())

    assert request.title == "Mi votación"
    assert len(request.option_texts) == 2


def test_create_poll_request_removes_extra_spaces():
    """Verify create poll request removes extra spaces."""
    data = valid_poll_data()
    data["title"] = "  Mi votación  "
    data["option_texts"] = ["  Opción A  ", "  Opción B  "]

    request = CreatePollRequest(**data)

    assert request.title == "Mi votación"
    assert request.option_texts == ["Opción A", "Opción B"]


def test_create_poll_request_rejects_empty_title():
    """Verify create poll request rejects empty title."""
    data = valid_poll_data()
    data["title"] = "   "

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_less_than_two_options():
    """Verify create poll request rejects less than two options."""
    data = valid_poll_data()
    data["option_texts"] = ["Opción A"]

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_empty_option():
    """Verify create poll request rejects empty option."""
    data = valid_poll_data()
    data["option_texts"] = ["Opción A", "   "]

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_zero_max_selections():
    """Verify create poll request rejects zero max selections."""
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 0

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_max_selections_above_options_count():
    """Verify create poll request rejects max selections above options count."""
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 3

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_max_selections_for_single_choice():
    """Verify create poll request rejects max selections for single choice."""
    data = valid_poll_data()
    data["max_selections"] = 1

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_accepts_valid_multiple_choice():
    """Verify create poll request accepts valid multiple choice."""
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 2

    request = CreatePollRequest(**data)

    assert request.max_selections == 2


def test_create_poll_request_rejects_datetime_without_timezone():
    """Verify create poll request rejects datetime without timezone."""
    data = valid_poll_data()
    data["closes_at"] = "2026-12-31T20:00:00"

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)