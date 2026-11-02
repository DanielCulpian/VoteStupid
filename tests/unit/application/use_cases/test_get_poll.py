from unittest.mock import create_autospec
from uuid import uuid4

from app.application.use_cases.get_poll import GetPoll
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.domain.repositories.poll_repository import PollRepository


def test_get_poll_returns_poll_when_it_exists():
    # Arrange: preparamos una votación y un repositorio simulado.
    poll_id = uuid4()

    poll = Poll(
        title="¿Cuál es la mejor opción?",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B")
        ]
    )

    repository = create_autospec(PollRepository, instance=True)
    repository.get_by_id.return_value = poll

    use_case = GetPoll(repository)

    # Act: ejecutamos el caso de uso.
    result = use_case.execute(poll_id)

    # Assert: comprobamos el resultado y la llamada al repositorio.
    assert result is poll
    repository.get_by_id.assert_called_once_with(poll_id)


def test_get_poll_returns_none_when_poll_does_not_exist():
    # Arrange: simulamos que el repositorio no encuentra la votación.
    poll_id = uuid4()

    repository = create_autospec(PollRepository, instance=True)
    repository.get_by_id.return_value = None

    use_case = GetPoll(repository)

    # Act: ejecutamos el caso de uso.
    result = use_case.execute(poll_id)

    # Assert: comprobamos que devuelve None.
    assert result is None
    repository.get_by_id.assert_called_once_with(poll_id)