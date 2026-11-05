import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.infrastructure.repositories.sqlalchemy_poll_repository import SqlAlchemyPollRepository
from app.presentation.api.dependencies import get_poll_repository


@pytest.fixture
def history_client(db_session):
    """Provide the real API with a repository connected only to the test database."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("poll_type", ["single_choice", "multiple_choice", "ranking"])
def test_public_history_queries_do_not_expose_admin_credentials(history_client, poll_type):
    """Verify public history queries do not expose admin credentials."""
    creation = history_client.post("/api/polls", json={
        "title": "Votación privada del organizador",
        "option_texts": ["A", "B"],
        "poll_type": poll_type,
    })
    assert creation.status_code == 201
    created = creation.json()
    for endpoint in [f"/api/polls/{created['id']}", f"/api/polls/{created['id']}/results"]:
        response = history_client.get(endpoint)
        assert response.status_code == 200
        serialized = json.dumps(response.json())
        assert created["admin_token"] not in serialized
        assert "admin_token" not in serialized
        assert "voter_token_hash" not in serialized


def test_history_does_not_add_a_public_poll_directory(history_client):
    """Verify history does not add a public poll directory."""
    assert history_client.get("/api/polls").status_code == 200
    assert history_client.get("/api/admin/polls").status_code == 200


def test_closed_poll_and_results_survive_new_connections_and_app_lifecycle(db_session, test_engine):
    """Verify closed poll and results survive new connections and app lifecycle."""
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            creation = client.post("/api/polls", json={
                "title": "Persistencia del histórico",
                "option_texts": ["A", "B"],
                "poll_type": "single_choice",
            })
            assert creation.status_code == 201
            created = creation.json()
            poll_id = created["id"]
            admin_headers = {"X-Admin-Token": created["admin_token"]}
            vote = client.post(
                f"/api/polls/{poll_id}/votes",
                headers={"X-Voter-Token": "participante-historico-de-prueba-123456789"},
                json={"selected_option_ids": [created["options"][0]["id"]]},
            )
            assert vote.status_code == 201
            assert client.put(f"/api/admin/polls/{poll_id}/close", headers=admin_headers).status_code == 200
            before = client.get(f"/api/polls/{poll_id}/results").json()

        db_session.close()
        test_engine.dispose()
        with Session(test_engine) as restored_session:
            restored_repository = SqlAlchemyPollRepository(restored_session)
            app.dependency_overrides[get_poll_repository] = lambda: restored_repository
            with TestClient(app) as restarted_client:
                restored_poll = restarted_client.get(f"/api/polls/{poll_id}")
                assert restored_poll.status_code == 200
                assert restored_poll.json()["is_active"] is False
                assert restored_poll.json()["created_at"] == created["created_at"]
                assert restarted_client.get(f"/api/polls/{poll_id}/results").json() == before
                assert before["total_votes"] == 1
                assert restarted_client.get(f"/api/admin/polls/{poll_id}", headers=admin_headers).status_code == 200
                assert restarted_client.get(f"/api/admin/polls/{poll_id}", headers={"X-Admin-Token": "incorrecto"}).status_code == 403
    finally:
        app.dependency_overrides.clear()
