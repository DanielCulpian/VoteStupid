import pytest
from pydantic import ValidationError

from app.domain.entities.poll_type import PollType
from app.presentation.api.schemas import CreatePollRequest


def valid_poll_data():
    """Proporciona datos válidos de creación de votaciones para las pruebas de esquemas."""
    return {
        "title": "Mi votación",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": PollType.SINGLE_CHOICE,
    }


def test_create_poll_request_accepts_valid_data():
    """Comprueba que el esquema de creación de votaciones acepta datos válidos."""
    request = CreatePollRequest(**valid_poll_data())

    assert request.title == "Mi votación"
    assert len(request.option_texts) == 2


def test_create_poll_request_removes_extra_spaces():
    """Comprueba que el esquema de creación de votaciones elimina los espacios sobrantes."""
    data = valid_poll_data()
    data["title"] = "  Mi votación  "
    data["option_texts"] = ["  Opción A  ", "  Opción B  "]

    request = CreatePollRequest(**data)

    assert request.title == "Mi votación"
    assert request.option_texts == ["Opción A", "Opción B"]


def test_create_poll_request_rejects_empty_title():
    """Comprueba que el esquema de creación de votaciones rechaza un título vacío."""
    data = valid_poll_data()
    data["title"] = "   "

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_less_than_two_options():
    """Comprueba que el esquema de creación de votaciones rechaza menos de dos opciones."""
    data = valid_poll_data()
    data["option_texts"] = ["Opción A"]

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_empty_option():
    """Comprueba que el esquema de creación de votaciones rechaza opciones vacías."""
    data = valid_poll_data()
    data["option_texts"] = ["Opción A", "   "]

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_zero_max_selections():
    """Comprueba que el esquema de creación de votaciones rechaza un límite de selecciones igual a cero."""
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 0

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_max_selections_above_options_count():
    """Comprueba que el esquema de creación de votaciones rechaza un límite mayor que el número de opciones."""
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 3

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_rejects_max_selections_for_single_choice():
    """Comprueba que el esquema de creación de votaciones rechaza un límite de selecciones en elección única."""
    data = valid_poll_data()
    data["max_selections"] = 1

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)


def test_create_poll_request_accepts_valid_multiple_choice():
    """Comprueba que el esquema de creación de votaciones acepta una configuración válida de elección múltiple."""
    data = valid_poll_data()
    data["poll_type"] = PollType.MULTIPLE_CHOICE
    data["max_selections"] = 2

    request = CreatePollRequest(**data)

    assert request.max_selections == 2


def test_create_poll_request_rejects_datetime_without_timezone():
    """Comprueba que el esquema de creación de votaciones rechaza fechas sin zona horaria."""
    data = valid_poll_data()
    data["closes_at"] = "2026-12-31T20:00:00"

    with pytest.raises(ValidationError):
        CreatePollRequest(**data)