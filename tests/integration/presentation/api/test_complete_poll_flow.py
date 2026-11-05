from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import create_app
from app.infrastructure.repositories.sqlalchemy_poll_repository import SqlAlchemyPollRepository
from app.presentation.api.dependencies import get_poll_repository


@contextmanager
def independent_client(engine, repository_class=SqlAlchemyPollRepository):
    """Create an API with one database session per request to test concurrent clients."""
    app = create_app()
    from app.infrastructure.security.admin_session import require_admin_session
    app.dependency_overrides[require_admin_session] = lambda: None

    def repository():
        """Provide an independent transaction and release the session afterwards."""
        with Session(engine) as session:
            yield repository_class(session)

    app.dependency_overrides[get_poll_repository] = repository
    with TestClient(app) as client:
        yield client


def create_poll(client, poll_type):
    """Create a three-option poll and retain the credential only within the test."""
    response = client.post("/api/polls", json={
        "title": "Flujo integral", "poll_type": poll_type, "option_texts": ["A", "B", "C"],
    })
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("poll_type,initial,updated,points", [
    ("single_choice", [[0], [1], [0]], [2], [1, 1, 1]),
    ("multiple_choice", [[0, 1], [1, 2], [0, 2]], [2], [1, 1, 3]),
    ("ranking", [[0, 1, 2], [1, 2, 0], [2, 0, 1]], [2, 1, 0], [1, 3, 5]),
])
def test_full_flow_broadcasts_exact_results_to_all_clients(test_engine, poll_type, initial, updated, points):
    """Verify full flow broadcasts exact results to all clients."""
    with independent_client(test_engine) as client:
        poll = create_poll(client, poll_type)
        other = create_poll(client, "single_choice")
        poll_id = poll["id"]
        ids = [option["id"] for option in poll["options"]]
        admin = {"X-Admin-Token": poll["admin_token"]}
        with (client.websocket_connect(f"/api/polls/{poll_id}/ws") as first,
              client.websocket_connect(f"/api/polls/{poll_id}/ws") as second,
              client.websocket_connect(f"/api/polls/{other['id']}/ws") as isolated):
            for index, selection in enumerate(initial):
                response = client.post(f"/api/polls/{poll_id}/votes", headers={"X-Voter-Token": str(index) * 40},
                                       json={"selected_option_ids": [ids[position] for position in selection]})
                assert response.status_code == 201
                expected = client.get(f"/api/polls/{poll_id}/results").json()
                assert first.receive_json() == second.receive_json() == {"type": "results_updated", "results": expected}
            response = client.put(f"/api/polls/{poll_id}/votes", headers={"X-Voter-Token": "0" * 40},
                                  json={"selected_option_ids": [ids[position] for position in updated]})
            assert response.status_code == 200
            results = client.get(f"/api/polls/{poll_id}/results").json()
            assert first.receive_json()["results"] == second.receive_json()["results"] == results
            assert results["total_votes"] == 3
            by_id = {item["option_id"]: item for item in results["results"]}
            for index, option_id in enumerate(ids):
                assert by_id[option_id]["points"] == points[index]
                denominator = 9 if poll_type == "ranking" else 3
                assert by_id[option_id]["percentage"] == pytest.approx(points[index] / denominator * 100)
                assert by_id[option_id]["votes"] == (3 if poll_type == "ranking" else points[index])

            # A rejection must not change results or add extra socket events.
            duplicate = client.post(f"/api/polls/{poll_id}/votes", headers={"X-Voter-Token": "0" * 40},
                                    json={"selected_option_ids": [ids[position] for position in updated]})
            assert duplicate.status_code == 409
            invalid = client.put(f"/api/polls/{poll_id}/votes", headers={"X-Voter-Token": "0" * 40},
                                  json={"selected_option_ids": [other["options"][0]["id"]]})
            assert invalid.status_code == 422
            for action, active in [("close", False), ("reopen", True)]:
                assert client.put(f"/api/admin/polls/{poll_id}/{action}", headers=admin).status_code == 200
                event = {"type": "poll_status_updated", "is_active": active}
                assert first.receive_json() == second.receive_json() == event
                if not active:
                    assert client.put(f"/api/polls/{poll_id}/votes", headers={"X-Voter-Token": "0" * 40},
                                      json={"selected_option_ids": [ids[position] for position in updated]}).status_code == 409
            assert client.get(f"/api/polls/{poll_id}/results").json() == results
            assert client.put(f"/api/admin/polls/{other['id']}/close",
                              headers={"X-Admin-Token": other["admin_token"]}).status_code == 200
            assert isolated.receive_json() == {"type": "poll_status_updated", "is_active": False}
        # A new subscription receives events after earlier clients disconnect.
        with client.websocket_connect(f"/api/polls/{poll_id}/ws") as restored:
            client.put(f"/api/admin/polls/{poll_id}/close", headers=admin)
            assert restored.receive_json() == {"type": "poll_status_updated", "is_active": False}


def test_same_voter_concurrent_requests_return_conflict_instead_of_server_error(test_engine):
    """Verify same voter concurrent requests return conflict instead of server error."""
    barrier = Barrier(2)

    class RacingRepository(SqlAlchemyPollRepository):
        def get_vote_by_voter(self, poll_id, voter_token_hash):
            """Synchronize both requests after checking that the vote does not yet exist."""
            result = super().get_vote_by_voter(poll_id, voter_token_hash)
            barrier.wait(timeout=10)
            return result

    with independent_client(test_engine) as client:
        poll = create_poll(client, "single_choice")

    def vote():
        """Send the same token through independent API and SQL sessions."""
        with independent_client(test_engine, RacingRepository) as client:
            return client.post(f"/api/polls/{poll['id']}/votes", headers={"X-Voter-Token": "same-voter-" + "x" * 32},
                               json={"selected_option_ids": [poll["options"][0]["id"]]}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: vote(), range(2)))
    assert sorted(codes) == [201, 409]
    with independent_client(test_engine) as client:
        assert client.get(f"/api/polls/{poll['id']}/results").json()["total_votes"] == 1


@pytest.mark.parametrize("poll_type", ["single_choice", "multiple_choice", "ranking"])
def test_independent_voters_can_vote_concurrently(test_engine, poll_type):
    """Verify independent voters can vote concurrently."""
    with independent_client(test_engine) as client:
        poll = create_poll(client, poll_type)
    ids = [option["id"] for option in poll["options"]]
    selection = ids if poll_type != "single_choice" else ids[:1]

    def vote(index):
        """Register a different participant using an independent database session."""
        with independent_client(test_engine) as client:
            return client.post(f"/api/polls/{poll['id']}/votes", headers={"X-Voter-Token": f"voter-{index}-" + "x" * 32},
                               json={"selected_option_ids": selection}).status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(vote, range(4))) == [201] * 4
    with independent_client(test_engine) as client:
        assert client.get(f"/api/polls/{poll['id']}/results").json()["total_votes"] == 4
