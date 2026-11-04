from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.entities.option import Option
from app.domain.entities.poll import Poll
from app.domain.entities.poll_type import PollType
from app.infrastructure.repositories.sqlalchemy_poll_repository import (
    SqlAlchemyPollRepository,
)
from app.presentation.api.dependencies import get_poll_repository

def test_get_poll_returns_200_when_poll_exists(db_session):
    """Comprueba que la consulta de votaciones responde con HTTP 200 cuando la votación existe."""
    # Arrange: guardamos una votación real en la base de datos de pruebas.
    poll = Poll(
        title="¿Cuál es la mejor opción?",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            # Act: consultamos la votación mediante HTTP.
            response = client.get(f"/api/polls/{poll.id}")

        # Assert: comprobamos la respuesta.
        assert response.status_code == 200

        data = response.json()

        assert data["id"] == str(poll.id)
        assert data["title"] == poll.title
        assert data["poll_type"] == "single_choice"
        assert len(data["options"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_get_poll_returns_404_when_poll_does_not_exist(db_session):
    """Comprueba que la consulta de votaciones responde con HTTP 404 cuando la votación no existe."""
    # Arrange: preparamos un repositorio sin esa votación.
    repository = SqlAlchemyPollRepository(db_session)

    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            # Act: consultamos un identificador inexistente.
            response = client.get(f"/api/polls/{uuid4()}")

        # Assert: comprobamos que devuelve 404.
        assert response.status_code == 404
        assert response.json()["detail"] == "La votación no existe."
    finally:
        app.dependency_overrides.clear()

def test_create_poll_returns_201_when_data_is_valid(db_session):
    """Comprueba que la creación de votaciones responde con HTTP 201 cuando los datos son válidos."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    payload = {
        "title": "¿Cuál es la mejor opción?",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": "single_choice",
    }

    try:
        with TestClient(app) as client:
            response = client.post("/api/polls", json=payload)

        assert response.status_code == 201

        data = response.json()
        assert data["title"] == payload["title"]
        assert len(data["options"]) == 2
        assert data["poll_type"] == "single_choice"
    finally:
        app.dependency_overrides.clear()

def test_get_admin_poll_returns_200_when_admin_token_is_valid(db_session):
    """Comprueba que el token privado permite consultar la votación sin revelar secretos."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    payload = {
        "title": "Votación administrada",
        "description": "Prueba de acceso al panel de administración.",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": "single_choice",
    }

    try:
        with TestClient(app) as client:
            # Arrange: creamos una votación y obtenemos su token privado real.
            creation_response = client.post("/api/polls", json=payload)
            assert creation_response.status_code == 201
            created_poll = creation_response.json()

            # Act: consultamos la administración con el token de esa votación.
            response = client.get(
                f"/api/admin/polls/{created_poll['id']}",
                headers={"X-Admin-Token": created_poll["admin_token"]},
            )

        # Assert: recibimos los datos guardados, sin el token ni su hash.
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_poll["id"]
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["poll_type"] == payload["poll_type"]
        assert data["options"] == created_poll["options"]
        assert data["is_active"] is True
        assert "admin_token" not in data
        assert "admin_token_hash" not in data
    finally:
        app.dependency_overrides.clear()


def test_get_admin_poll_returns_403_when_admin_token_is_invalid(db_session):
    """Comprueba que un token incorrecto impide consultar los datos de administración."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    payload = {
        "title": "Votación protegida",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": "single_choice",
    }

    try:
        with TestClient(app) as client:
            # Arrange: creamos una votación con un token privado real.
            creation_response = client.post("/api/polls", json=payload)
            assert creation_response.status_code == 201
            created_poll = creation_response.json()

            # Act: enviamos un token distinto al generado para esta votación.
            response = client.get(
                f"/api/admin/polls/{created_poll['id']}",
                headers={"X-Admin-Token": created_poll["admin_token"] + "-incorrecto"},
            )

        # Assert: solo se devuelve el error, sin datos de la votación ni secretos.
        assert response.status_code == 403
        assert response.json() == {"detail": "Token de administrador inválido."}
    finally:
        app.dependency_overrides.clear()


def test_create_poll_returns_422_when_title_is_empty(db_session):
    """Comprueba que la creación de votaciones responde con HTTP 422 cuando el título está vacío."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    payload = {
        "title": "   ",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": "single_choice",
    }

    try:
        with TestClient(app) as client:
            response = client.post("/api/polls", json=payload)

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

def test_create_poll_returns_422_when_max_selections_is_invalid(db_session):
    """Comprueba que la creación de votaciones responde con HTTP 422 ante un límite de selecciones inválido."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    payload = {
        "title": "¿Cuál es la mejor opción?",
        "option_texts": ["Opción A", "Opción B"],
        "poll_type": "single_choice",
        "max_selections": 1,
    }

    try:
        with TestClient(app) as client:
            response = client.post("/api/polls", json=payload)

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

def test_cast_vote_returns_201_when_data_is_valid(db_session):
    """Comprueba que el registro de votos responde con HTTP 201 cuando los datos son válidos."""
    # Arrange
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    app.dependency_overrides[get_poll_repository] = lambda: repository

    voter_token = "a" * 40
    selected_option_id = poll.options[0].id

    try:
        with TestClient(app) as client:
            # Act
            response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={"selected_option_ids": [str(selected_option_id)]},
                headers={"X-Voter-Token": voter_token},
            )

        # Assert
        assert response.status_code == 201

        data = response.json()
        assert data["poll_id"] == str(poll.id)
        assert data["selected_option_ids"] == [str(selected_option_id)]
        assert "voter_token_hash" not in data
    finally:
        app.dependency_overrides.clear()


def test_cast_vote_returns_409_when_voter_has_already_voted(db_session):
    """Comprueba que el registro de votos responde con HTTP 409 si el participante ya ha votado."""
    # Arrange
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    app.dependency_overrides[get_poll_repository] = lambda: repository

    voter_token = "b" * 40
    payload = {
        "selected_option_ids": [str(poll.options[0].id)]
    }
    headers = {"X-Voter-Token": voter_token}

    try:
        with TestClient(app) as client:
            first_response = client.post(
                f"/api/polls/{poll.id}/votes",
                json=payload,
                headers=headers,
            )

            second_response = client.post(
                f"/api/polls/{poll.id}/votes",
                json=payload,
                headers=headers,
            )

        # Assert
        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json()["detail"] == (
            "Este participante ya ha votado."
        )
    finally:
        app.dependency_overrides.clear()


def test_cast_vote_returns_422_when_voter_token_is_missing(db_session):
    """Comprueba que el registro de votos responde con HTTP 422 si falta el token del participante."""
    # Arrange
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            # Act
            response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [
                        str(poll.options[0].id)
                    ]
                },
            )

        # Assert
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_cast_vote_returns_422_when_option_does_not_belong_to_poll(
    db_session,
):
    """Comprueba que el registro de votos responde con HTTP 422 ante una opción de otra votación."""
    # Arrange
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            # Act
            response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={"selected_option_ids": [str(uuid4())]},
                headers={"X-Voter-Token": "c" * 40},
            )

        # Assert
        assert response.status_code == 422
        assert "no pertenecen" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_cast_vote_returns_409_when_poll_is_closed(db_session):
    """Comprueba que el registro de votos responde con HTTP 409 si la votación está cerrada."""
    # Arrange
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
        is_active=False,
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)

    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            # Act
            response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [
                        str(poll.options[0].id)
                    ]
                },
                headers={"X-Voter-Token": "d" * 40},
            )

        # Assert
        assert response.status_code == 409
        assert response.json()["detail"] == "La votación está cerrada."
    finally:
        app.dependency_overrides.clear()

def test_update_vote_returns_200_when_vote_exists(db_session):
    """Comprueba que la actualización de votos responde con HTTP 200 al modificar un voto existente."""
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    voter_token = "e" * 40
    headers = {"X-Voter-Token": voter_token}

    try:
        with TestClient(app) as client:
            first_response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [str(poll.options[0].id)]
                },
                headers=headers,
            )

            response = client.put(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [str(poll.options[1].id)]
                },
                headers=headers,
            )

        assert first_response.status_code == 201
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == first_response.json()["id"]
        assert data["selected_option_ids"] == [str(poll.options[1].id)]
    finally:
        app.dependency_overrides.clear()

def test_update_vote_returns_404_when_voter_has_not_voted(db_session):
    """Comprueba que la actualización de votos responde con HTTP 404 si el participante no ha votado."""
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            response = client.put(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [str(poll.options[0].id)]
                },
                headers={"X-Voter-Token": "f" * 40},
            )

        assert response.status_code == 404, response.text
        assert response.json()["detail"] == (
            "Este participante todavía no ha votado."
        )
    finally:
        app.dependency_overrides.clear()

def test_update_vote_returns_409_when_poll_is_closed(db_session):
    """Comprueba que la actualización de votos responde con HTTP 409 si la votación está cerrada."""
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    voter_token = "g" * 40
    headers = {"X-Voter-Token": voter_token}

    try:
        with TestClient(app) as client:
            first_response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [str(poll.options[0].id)]
                },
                headers=headers,
            )

            poll.is_active = False
            repository.update_poll(poll)

            response = client.put(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [str(poll.options[1].id)]
                },
                headers=headers,
            )

        assert first_response.status_code == 201
        assert response.status_code == 409
        assert response.json()["detail"] == "La votación está cerrada."
    finally:
        app.dependency_overrides.clear()

def test_update_vote_returns_422_when_selection_is_invalid(db_session):
    """Comprueba que la actualización de votos responde con HTTP 422 ante una selección inválida."""
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    voter_token = "h" * 40
    headers = {"X-Voter-Token": voter_token}

    try:
        with TestClient(app) as client:
            first_response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [str(poll.options[0].id)]
                },
                headers=headers,
            )

            response = client.put(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [
                        str(poll.options[0].id),
                        str(poll.options[1].id),
                    ]
                },
                headers=headers,
            )

        assert first_response.status_code == 201
        assert response.status_code == 422
        assert "exactamente una opción" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

def test_get_poll_results_returns_200_when_poll_has_votes(db_session):
    """Comprueba que la consulta de resultados responde con HTTP 200 cuando hay votos."""
    poll = Poll(
        title="Mejor opción",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
            Option(text="Opción C"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            votes = [
                (poll.options[0], "i" * 40),
                (poll.options[0], "j" * 40),
                (poll.options[1], "k" * 40),
            ]

            for option, token in votes:
                response = client.post(
                    f"/api/polls/{poll.id}/votes",
                    json={"selected_option_ids": [str(option.id)]},
                    headers={"X-Voter-Token": token},
                )
                assert response.status_code == 201

            response = client.get(
                f"/api/polls/{poll.id}/results"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["poll_id"] == str(poll.id)
        assert data["poll_title"] == poll.title
        assert data["total_votes"] == 3

        results = data["results"]

        assert results[0]["option_text"] == "Opción A"
        assert results[0]["votes"] == 2
        assert results[0]["points"] == 2
        assert results[0]["percentage"] == pytest.approx(66.67, abs=0.01)

        assert results[1]["option_text"] == "Opción B"
        assert results[1]["votes"] == 1
        assert results[1]["percentage"] == pytest.approx(33.33, abs=0.01)

        assert results[2]["option_text"] == "Opción C"
        assert results[2]["votes"] == 0

        assert "voter_token_hash" not in data
    finally:
        app.dependency_overrides.clear()


def test_get_poll_results_returns_zero_when_poll_has_no_votes(db_session):
    """Comprueba que la consulta de resultados devuelve valores a cero cuando no hay votos."""
    poll = Poll(
        title="Votación sin participantes",
        poll_type=PollType.SINGLE_CHOICE,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/polls/{poll.id}/results"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["total_votes"] == 0

        for result in data["results"]:
            assert result["votes"] == 0
            assert result["points"] == 0
            assert result["percentage"] == 0
    finally:
        app.dependency_overrides.clear()


def test_get_poll_results_returns_404_when_poll_does_not_exist(db_session):
    """Comprueba que la consulta de resultados responde con HTTP 404 cuando la votación no existe."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/polls/{uuid4()}/results"
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "La votación no existe."
    finally:
        app.dependency_overrides.clear()


def test_get_poll_results_calculates_ranking_points(db_session):
    """Comprueba que la consulta de resultados calcula los puntos del ranking."""
    poll = Poll(
        title="Ranking de opciones",
        poll_type=PollType.RANKING,
        options=[
            Option(text="Opción A"),
            Option(text="Opción B"),
            Option(text="Opción C"),
        ],
    )

    repository = SqlAlchemyPollRepository(db_session)
    repository.save_poll(poll)
    app.dependency_overrides[get_poll_repository] = lambda: repository

    first_voter = "l" * 40
    second_voter = "m" * 40

    try:
        with TestClient(app) as client:
            first_response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [
                        str(poll.options[0].id),
                        str(poll.options[1].id),
                        str(poll.options[2].id),
                    ]
                },
                headers={"X-Voter-Token": first_voter},
            )

            second_response = client.post(
                f"/api/polls/{poll.id}/votes",
                json={
                    "selected_option_ids": [
                        str(poll.options[1].id),
                        str(poll.options[2].id),
                        str(poll.options[0].id),
                    ]
                },
                headers={"X-Voter-Token": second_voter},
            )

            response = client.get(
                f"/api/polls/{poll.id}/results"
            )

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        assert response.status_code == 200

        data = response.json()

        assert data["total_votes"] == 2

        results = data["results"]

        assert results[0]["points"] == 2
        assert results[0]["percentage"] == pytest.approx(33.33, abs=0.01)

        assert results[1]["points"] == 3
        assert results[1]["percentage"] == 50

        assert results[2]["points"] == 1
        assert results[2]["percentage"] == pytest.approx(16.67, abs=0.01)
    finally:
        app.dependency_overrides.clear()
