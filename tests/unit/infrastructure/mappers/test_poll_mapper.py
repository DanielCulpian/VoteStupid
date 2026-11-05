from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.infrastructure.mappers.poll_mapper import to_model
from app.infrastructure.mappers.poll_mapper import to_model, to_entity

def test_to_model_converts_poll_and_options():
    """Verify to model converts poll and options."""
    option_1 = Option(text="Matrix")
    option_2 = Option(text="Interestelar")

    poll = Poll(
        title="¿Qué película vemos?",
        poll_type=PollType.SINGLE_CHOICE,
        options=[option_1, option_2],
    )

    result = to_model(poll)

    assert result.id == poll.id
    assert result.title == poll.title
    assert result.poll_type == "single_choice"
    assert len(result.options) == 2

    assert result.options[0].id == option_1.id
    assert result.options[0].text == "Matrix"

    assert result.options[1].id == option_2.id
    assert result.options[1].text == "Interestelar"

def test_to_entity_converts_model_and_options():
    """Verify to entity converts model and options."""
    option_1 = Option(text="Matrix")
    option_2 = Option(text="Interestelar")

    poll = Poll(
        title="¿Qué película vemos?",
        poll_type=PollType.MULTIPLE_CHOICE,
        options=[option_1, option_2],
        max_selections=2
    )

    model = to_model(poll)

    result = to_entity(model)

    assert result.id == poll.id
    assert result.title == poll.title
    assert result.poll_type == poll.poll_type
    assert result.max_selections == poll.max_selections
    assert len(result.options) == 2

    assert result.options[0].id == option_1.id
    assert result.options[0].text == "Matrix"

    assert result.options[1].id == option_2.id
    assert result.options[1].text == "Interestelar"