import pytest
from pydantic import ValidationError

from app.domain.entities.poll_type import PollType
from app.presentation.api.schemas import CreatePollRequest


def valid_poll_data():
    return {
        "title": "Mi votación",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": PollType.SINGLE_CHOICE,
    }


def test_create_poll_request_accepts_valid_data():
    request = CreatePollRequest(**valid_poll_data())

    assert request.title == "Mi votación"
    assert len(request.option_texts) == 2


def test_create_poll_request_removes_extra_spaces():
    data = valid_poll_data()
    data["title"] = "  Mi votación  "
    data["option_texts"] = ["  Opción A  ", "  Opción B  "]

    request = CreatePollRequest(**data)

    assert request.title == "Mi votación"
    assert request.option_texts == ["Opción A", "Opción B"]


def test_create_poll_request_rejects_empty_title():
    data = valid_poll_data()
    data["title"] = "   "

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_less_than_two_options():
    data = valid_poll_data()
    data["option_texts"] = ["Opción A"]

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_empty_option():
    data = valid_poll_data()
    data["option_texts"] = ["Opción A", "   "]

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_zero_max_selections():
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 0

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_max_selections_above_options_count():
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 3

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_max_selections_for_single_choice():
    data = valid_poll_data()
    data["max_selections"] = 1

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_accepts_valid_multiple_choice():
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 2

    request = CreatePollRequest(**data)

    assert request.max_selections == 2


def test_create_poll_request_rejects_datetime_without_timezone():
    data = valid_poll_data()
    data["closes_at"] = "2026-12-31T20:00:00"

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)