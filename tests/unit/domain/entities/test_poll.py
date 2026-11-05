import pytest

from datetime import datetime
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType

def test_create_valid_poll():
    """Verify create valid poll."""
    options = [
        Option(text="Ir al cine"),
        Option(text="Ir a cenar"),
        Option(text="Jugar a los bolos")
    ]

    poll = Poll(
        title="¿Qué hacemos el sábado?",
        poll_type=PollType.SINGLE_CHOICE,
        options=options
    )

    assert poll.title == "¿Qué hacemos el sábado?"
    assert poll.poll_type == PollType.SINGLE_CHOICE
    assert len(poll.options) == 3
    assert poll.is_active is True
    assert poll.id is not None
    assert poll.created_at is not None

def test_poll_requires_title():
    """Verify poll requires title."""
    options = [
        Option(text="Opción 1"),
        Option(text="Opción 2")
    ]

    with pytest.raises(ValueError):
        Poll(
            title="   ",
            poll_type=PollType.SINGLE_CHOICE,
            options=options
        )


def test_poll_requires_at_least_two_options():
    """Verify poll requires at least two options."""
    options = [
        Option(text="Opción 1")
    ]

    with pytest.raises(ValueError):
        Poll(
            title="Votación de prueba",
            poll_type=PollType.SINGLE_CHOICE,
            options=options
        )


def test_multiple_choice_rejects_too_many_selections():
    """Verify multiple choice rejects too many selections."""
    options = [
        Option(text="Opción 1"),
        Option(text="Opción 2"),
        Option(text="Opción 3")
    ]

    with pytest.raises(ValueError):
        Poll(
            title="Votación de prueba",
            poll_type=PollType.MULTIPLE_CHOICE,
            options=options,
            max_selections=5
        )

def test_multiple_choice_rejects_zero_selections():
    """Verify multiple choice rejects zero selections."""
    options = [
        Option(text="Opción 1"),
        Option(text="Opción 2")
    ]

    with pytest.raises(ValueError):
        Poll(
            title="Votación de prueba",
            poll_type=PollType.MULTIPLE_CHOICE,
            options=options,
            max_selections=0
        )


def test_single_choice_rejects_max_selections():
    """Verify single choice rejects max selections."""
    options = [
        Option(text="Opción 1"),
        Option(text="Opción 2")
    ]

    with pytest.raises(ValueError):
        Poll(
            title="Votación de prueba",
            poll_type=PollType.SINGLE_CHOICE,
            options=options,
            max_selections=2
        )

def test_poll_rejects_closes_at_without_timezone():
    """Verify poll rejects closes at without timezone."""
    options = [
        Option(text="Ir al cine"),
        Option(text="Ir a cenar")
    ]

    with pytest.raises(
        ValueError,
        match="La fecha de cierre debe incluir una zona horaria."
    ):
        Poll(
            title="¿Qué hacemos el sábado?",
            poll_type=PollType.SINGLE_CHOICE,
            options=options,
            closes_at=datetime(2026, 12, 31, 23, 59)
        )
