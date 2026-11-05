import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import create_app
from app.infrastructure.repositories.sqlalchemy_poll_repository import SqlAlchemyPollRepository
from app.presentation.api.dependencies import get_poll_repository


@pytest.fixture
def secure_client(db_session):
    """Use the PostgreSQL test database with all protections enabled on a new API instance."""
    app = create_app()
    from app.infrastructure.security.admin_session import require_admin_session
    app.dependency_overrides[require_admin_session] = lambda: None
    repository = SqlAlchemyPollRepository(db_session)
    app.dependency_overrides[get_poll_repository] = lambda: repository
    with TestClient(app) as client:
        yield client


def poll_data(**changes):
    """Build a valid request and allow overriding a specific limit."""
    return {"title": "Prueba de seguridad", "option_texts": ["A", "B"], "poll_type": "single_choice", **changes}


@pytest.mark.parametrize("changes", [
    {"title": "x" * 256}, {"description": "x" * 5001},
    {"option_texts": ["A", "x" * 256]}, {"option_texts": ["x"] * 51},
    {"title": "   "}, {"option_texts": ["A", "   "]},
    {"max_selections": True}, {"closes_at": "not-a-date"},
    {"admin_token": "injected-secret"}, {"is_active": False},
])
def test_rejects_invalid_creation_before_database(secure_client, changes):
    """Verify rejects invalid creation before database."""
    response = secure_client.post("/api/polls", json=poll_data(**changes))
    assert response.status_code == 422
    assert "input" not in response.text
    assert "injected-secret" not in response.text


def test_accepts_exact_limits(secure_client):
    """Verify accepts exact limits."""
    response = secure_client.post("/api/polls", json=poll_data(
        title="x" * 255, description="d" * 5000,
        option_texts=["o" * 255 for _ in range(50)], poll_type="ranking",
    ))
    assert response.status_code == 201
    assert len(response.json()["options"]) == 50


@pytest.mark.parametrize("method", ["post", "put"])
def test_rejects_unbounded_vote_selection(secure_client, method):
    """Verify rejects unbounded vote selection."""
    response = getattr(secure_client, method)(f"/api/polls/{uuid4()}/votes",
        json={"selected_option_ids": [str(uuid4()) for _ in range(51)]},
        headers={"X-Voter-Token": "v" * 40})
    assert response.status_code == 422


@pytest.mark.parametrize("poll_type", ["single_choice", "multiple_choice", "ranking"])
def test_normal_voting_administration_and_events_remain_available(secure_client, poll_type):
    """Verify normal voting administration and events remain available."""
    created = secure_client.post("/api/polls", json=poll_data(poll_type=poll_type)).json()
    poll_id = created["id"]
    admin = {"X-Admin-Token": created["admin_token"]}
    options = [option["id"] for option in created["options"]]
    selected = options if poll_type != "single_choice" else options[:1]
    updated = list(reversed(options)) if poll_type == "ranking" else options[-1:]
    with secure_client.websocket_connect(f"/api/polls/{poll_id}/ws") as socket:
        for index in range(5):
            headers = {"X-Voter-Token": f"participant-{index}-" + "x" * 32}
            vote = secure_client.post(f"/api/polls/{poll_id}/votes", json={"selected_option_ids": selected}, headers=headers)
            assert vote.status_code == 201
            assert socket.receive_json()["type"] == "results_updated"
            vote = secure_client.put(f"/api/polls/{poll_id}/votes", json={"selected_option_ids": updated}, headers=headers)
            assert vote.status_code == 200
            assert socket.receive_json()["type"] == "results_updated"
        for suffix, method in [("", "get"), ("/close", "put"), ("/reopen", "put")]:
            denied = getattr(secure_client, method)(f"/api/admin/polls/{poll_id}{suffix}", headers={"X-Admin-Token": "wrong" * 10})
            assert denied.status_code == 403
        for action, active in [("close", False), ("reopen", True)]:
            response = secure_client.put(f"/api/admin/polls/{poll_id}/{action}", headers=admin)
            assert response.status_code == 200
            assert socket.receive_json() == {"type": "poll_status_updated", "is_active": active}
        results = secure_client.get(f"/api/polls/{poll_id}/results")
        assert results.json()["total_votes"] == 5
        for path in [f"/api/polls/{poll_id}", f"/api/polls/{poll_id}/results", f"/api/admin/polls/{poll_id}"]:
            response = secure_client.get(path, headers=admin)
            assert response.status_code == 200
            assert created["admin_token"] not in response.text
            assert "token_hash" not in response.text
            assert response.headers["Cache-Control"] == "no-store"


def test_real_admin_attempts_are_rate_limited(secure_client):
    """Verify real admin attempts are rate limited."""
    created = secure_client.post("/api/polls", json=poll_data()).json()
    for _ in range(30):
        response = secure_client.get(f"/api/admin/polls/{created['id']}", headers={"X-Admin-Token": "wrong" * 10})
        assert response.status_code == 403
    response = secure_client.get(f"/api/admin/polls/{created['id']}", headers={"X-Admin-Token": created["admin_token"]})
    assert response.status_code == 429
    assert response.headers["Retry-After"]
    assert secure_client.get(f"/api/polls/{created['id']}").status_code == 200
