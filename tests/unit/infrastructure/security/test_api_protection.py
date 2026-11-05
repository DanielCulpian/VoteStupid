import asyncio
import logging

import pytest
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.main import create_app as protected_app
from app.infrastructure.security.admin_session import require_admin_session
from app.infrastructure.security.api_protection import ApiProtection, RateLimiter, SafeAccessLog, allowed_origins



def create_app():
    """Test validation and rate limits for an authorized organizer without bypassing protections."""
    app = protected_app()
    app.dependency_overrides[require_admin_session] = lambda: None
    return app


def test_limiter_window_and_bounded_storage():
    """Verify limiter window and bounded storage."""
    now = [0]
    limiter = RateLimiter(clock=lambda: now[0], max_keys=2)
    for _ in range(10):
        assert limiter.check("client", "create") == 0
    assert limiter.check("client", "create") == 60
    assert limiter.check("other", "create") == 60
    now[0] = 59.2
    assert limiter.check("client", "create") == 1
    now[0] = 60
    assert limiter.check("other", "create") == 0
    assert len(limiter.buckets) == 2


@pytest.mark.parametrize("path,method,limit", [
    ("/api/polls", "POST", 10),
    ("/api/polls/not-a-uuid/votes", "POST", 30),
    ("/api/polls/not-a-uuid/votes", "PUT", 30),
    ("/api/admin/polls/not-a-uuid", "GET", 30),
    ("/api/admin/polls/not-a-uuid/close", "PUT", 30),
    ("/api/status", "GET", 300),
])
def test_api_returns_429_without_disabling_protection(path, method, limit):
    """Verify api returns 429 without disabling protection."""
    with TestClient(create_app()) as client:
        for _ in range(limit):
            assert client.request(method, path, json={}).status_code != 429
        response = client.request(method, path, json={})
    assert response.status_code == 429
    assert 1 <= int(response.headers["Retry-After"]) <= 60
    assert response.headers["Cache-Control"] == "no-store"


def test_changing_poll_ids_tokens_or_forwarded_headers_does_not_reset_limits():
    """Verify changing poll ids tokens or forwarded headers does not reset limits."""
    with TestClient(create_app()) as client:
        for index in range(30):
            response = client.get(f"/api/admin/polls/invalid-{index}", headers={
                "X-Admin-Token": "x" * 32 + str(index),
                "X-Forwarded-For": f"192.0.2.{index}",
                "CF-Connecting-IP": f"192.0.2.{index}",
            })
            assert response.status_code != 429
        assert client.get("/api/admin/polls/invalid").status_code == 429
        assert client.get("/api/status").status_code == 200


def test_trusted_uvicorn_proxy_preserves_separate_client_limits():
    """Verify trusted uvicorn proxy preserves separate client limits."""
    app = ProxyHeadersMiddleware(create_app(), trusted_hosts=["testclient"])
    with TestClient(app) as client:
        for _ in range(10):
            assert client.post("/api/polls", json={}, headers={"X-Forwarded-For": "192.0.2.1"}).status_code == 422
        assert client.post("/api/polls", json={}, headers={"X-Forwarded-For": "192.0.2.1"}).status_code == 429
        assert client.post("/api/polls", json={}, headers={"X-Forwarded-For": "192.0.2.2"}).status_code == 422


@pytest.mark.parametrize("origin", ["*", "https://example.com/path", "https://user:pass@example.com", "https://*.example.com"])
def test_cors_rejects_unsafe_configuration(monkeypatch, origin):
    """Verify cors rejects unsafe configuration."""
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origin)
    with pytest.raises(ValueError):
        allowed_origins()


def test_cors_is_explicit_and_survives_errors(monkeypatch):
    """Verify cors is explicit and survives errors."""
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://vote.example.com")
    app = create_app()

    @app.get("/fail")
    def fail():
        """Simulate an internal failure without accessing real data."""
        raise RuntimeError("private-database-password")

    with TestClient(app) as client:
        assert client.options("/api/polls", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"}).status_code == 400
        response = client.options("/api/polls", headers={"Origin": "https://vote.example.com", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "X-Voter-Token,Content-Type"})
        assert response.status_code == 200
        failure = client.get("/fail", headers={"Origin": "https://vote.example.com"})
        assert failure.status_code == 500
        assert failure.headers["Access-Control-Allow-Origin"] == "https://vote.example.com"
        for _ in range(10):
            client.post("/api/polls", json={})
        limited = client.post("/api/polls", json={}, headers={"Origin": "https://vote.example.com"})
        assert limited.status_code == 429
        assert limited.headers["Access-Control-Allow-Origin"] == "https://vote.example.com"


def test_internal_errors_and_validation_do_not_expose_secrets(caplog):
    """Verify internal errors and validation do not expose secrets."""
    secret = "secret-admin-password-" * 20
    app = create_app()

    @app.get("/fail")
    def fail():
        """Simulate an exception that could contain database credentials."""
        raise RuntimeError(secret)

    with TestClient(app) as client:
        response = client.post("/api/polls", json={"title": secret, "admin_token": secret})
        assert response.status_code == 422
        assert secret not in response.text
        assert all("input" not in item and "ctx" not in item for item in response.json()["detail"])
        response = client.get("/fail")
        assert response.status_code == 500
        assert secret not in response.text
        assert secret not in caplog.text
        assert response.headers["Cache-Control"] == "no-store"
        response = client.post("/api/polls/invalid/votes", json={"selected_option_ids": []}, headers={"X-Voter-Token": secret})
        assert response.status_code == 422
        assert secret not in response.text


def test_access_logs_omit_query_secrets():
    """Verify access logs omit query secrets."""
    record = logging.LogRecord("uvicorn.access", 20, "", 0, '%s - "%s %s HTTP/%s" %d',
                               ("client", "GET", "/api/status?token=private-value", "1.1", 200), None)
    assert SafeAccessLog().filter(record)
    assert "private-value" not in record.getMessage()
    record = logging.LogRecord("uvicorn.error", 20, "", 0, '%s - "WebSocket %s" [accepted]',
                               ("client", "/api/polls/id/ws?token=private-value"), None)
    assert SafeAccessLog().filter(record)
    assert "private-value" not in record.getMessage()


@pytest.mark.parametrize("method", ["post", "put"])
def test_unexpected_vote_value_errors_remain_private(method, caplog):
    """Verify unexpected vote value errors remain private."""
    from app.presentation.api.dependencies import get_cast_vote_use_case, get_update_vote_use_case
    from uuid import uuid4

    class FailingVote:
        def execute(self, **kwargs):
            """Simulate an internal failure containing a secret and public error wording."""
            raise ValueError("private-value no existe")

    app = create_app()
    dependency = get_cast_vote_use_case if method == "post" else get_update_vote_use_case
    app.dependency_overrides[dependency] = FailingVote
    with TestClient(app) as client:
        response = getattr(client, method)(f"/api/polls/{uuid4()}/votes",
            json={"selected_option_ids": [str(uuid4())]}, headers={"X-Voter-Token": "v" * 40})
        assert response.status_code == 500
        assert "private-value" not in response.text
        assert "private-value" not in caplog.text


def test_websocket_binary_input_is_closed_without_internal_error():
    """Verify websocket binary input is closed without internal error."""
    from uuid import uuid4
    from starlette.websockets import WebSocketDisconnect
    from app.infrastructure.realtime.connection_manager import connection_manager

    poll_id = uuid4()
    with TestClient(create_app()) as client:
        with client.websocket_connect(f"/api/polls/{poll_id}/ws") as socket:
            socket.send_bytes(b"unexpected input")
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_json()
            assert error.value.code == 1008
    assert poll_id not in connection_manager.active_connections


def test_oversized_bodies_are_rejected_with_or_without_content_length():
    """Verify oversized bodies are rejected with or without content length."""
    async def scenario():
        """Invoke ASGI directly to represent a real chunked request."""
        messages = iter([{"type": "http.request", "body": b"x" * 40000, "more_body": True},
                         {"type": "http.request", "body": b"x" * 40000, "more_body": False}])
        sent = []

        async def receive():
            """Deliver the next request chunk."""
            return next(messages)

        async def send(message):
            """Capture the middleware response."""
            sent.append(message)

        async def unreachable(scope, receive, send):
            """Prevent an oversized body from reaching the routes."""
            pytest.fail("El cuerpo excesivo alcanzó el endpoint")

        await ApiProtection(unreachable, RateLimiter(), [])({"type": "http", "path": "/api/polls", "method": "POST", "headers": [], "client": ("client", 1)}, receive, send)
        assert sent[0]["status"] == 413

    asyncio.run(scenario())
    with TestClient(create_app()) as client:
        assert client.post("/api/polls", content=b"x" * 65537).status_code == 413


def test_websocket_origins_rate_and_cleanup(monkeypatch):
    """Verify websocket origins rate and cleanup."""
    from contextlib import ExitStack
    from uuid import uuid4
    from starlette.websockets import WebSocketDisconnect
    from starlette.testclient import WebSocketDenialResponse

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    with TestClient(create_app()) as client:
        path = f"/api/polls/{uuid4()}/ws"
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(path, headers={"Origin": "https://evil.example"}):
                pass
        with ExitStack() as stack:
            for _ in range(20):
                stack.enter_context(client.websocket_connect(path))
            # TestClient supports HTTP denials and closures before WebSocket acceptance.
            with pytest.raises((WebSocketDisconnect, WebSocketDenialResponse)):
                stack.enter_context(client.websocket_connect(path))
        with client.websocket_connect(path, headers={"Origin": "http://localhost:5173"}):
            pass
        for _ in range(7):
            with client.websocket_connect(path):
                pass
        with pytest.raises((WebSocketDisconnect, WebSocketDenialResponse)):
            with client.websocket_connect(path):
                pass
