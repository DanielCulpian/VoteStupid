import asyncio
import logging

import pytest
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.main import create_app
from app.infrastructure.security.api_protection import ApiProtection, RateLimiter, SafeAccessLog, allowed_origins


def test_limiter_window_and_bounded_storage():
    """Comprueba el cupo por operación, su caducidad y el límite de memoria."""
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
    """Verifica cupos reales incluso para peticiones inválidas o sin credenciales."""
    with TestClient(create_app()) as client:
        for _ in range(limit):
            assert client.request(method, path, json={}).status_code != 429
        response = client.request(method, path, json={})
    assert response.status_code == 429
    assert 1 <= int(response.headers["Retry-After"]) <= 60
    assert response.headers["Cache-Control"] == "no-store"


def test_changing_poll_ids_tokens_or_forwarded_headers_does_not_reset_limits():
    """Impide esquivar el cupo rotando identificadores, tokens o cabeceras de IP falsas."""
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
    """Comprueba que solo Uvicorn y un proxy explícitamente autorizado determinan la IP."""
    app = ProxyHeadersMiddleware(create_app(), trusted_hosts=["testclient"])
    with TestClient(app) as client:
        for _ in range(10):
            assert client.post("/api/polls", json={}, headers={"X-Forwarded-For": "192.0.2.1"}).status_code == 422
        assert client.post("/api/polls", json={}, headers={"X-Forwarded-For": "192.0.2.1"}).status_code == 429
        assert client.post("/api/polls", json={}, headers={"X-Forwarded-For": "192.0.2.2"}).status_code == 422


@pytest.mark.parametrize("origin", ["*", "https://example.com/path", "https://user:pass@example.com", "https://*.example.com"])
def test_cors_rejects_unsafe_configuration(monkeypatch, origin):
    """Rechaza comodines, credenciales y rutas en la configuración de orígenes."""
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origin)
    with pytest.raises(ValueError):
        allowed_origins()


def test_cors_is_explicit_and_survives_errors(monkeypatch):
    """Comprueba preflight autorizado y que 429 y 500 conservan las cabeceras CORS."""
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://vote.example.com")
    app = create_app()

    @app.get("/fail")
    def fail():
        """Simula un fallo interno sin acceso a datos reales."""
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
    """Comprueba que ni respuestas ni logs repiten secretos de cuerpos o excepciones."""
    secret = "secret-admin-password-" * 20
    app = create_app()

    @app.get("/fail")
    def fail():
        """Simula una excepción que podría incluir credenciales de base de datos."""
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
    """Elimina tokens enviados por error como parámetros antes de emitir el log de Uvicorn."""
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
    """Evita confundir un ValueError interno con un rechazo público de las reglas del voto."""
    from app.presentation.api.dependencies import get_cast_vote_use_case, get_update_vote_use_case
    from uuid import uuid4

    class FailingVote:
        def execute(self, **kwargs):
            """Simula un fallo interno que contiene un secreto y palabras de un error público."""
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
    """Rechaza mensajes binarios en el canal de publicación y libera su registro."""
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
    """Bloquea cuerpos grandes antes del esquema aunque lleguen por fragmentos sin longitud."""
    async def scenario():
        """Ejecuta ASGI directamente para representar una petición fragmentada real."""
        messages = iter([{"type": "http.request", "body": b"x" * 40000, "more_body": True},
                         {"type": "http.request", "body": b"x" * 40000, "more_body": False}])
        sent = []

        async def receive():
            """Entrega el siguiente fragmento de la petición."""
            return next(messages)

        async def send(message):
            """Captura la respuesta del middleware."""
            sent.append(message)

        async def unreachable(scope, receive, send):
            """Impide que un cuerpo excesivo llegue a las rutas."""
            pytest.fail("El cuerpo excesivo alcanzó el endpoint")

        await ApiProtection(unreachable, RateLimiter(), [])({"type": "http", "path": "/api/polls", "method": "POST", "headers": [], "client": ("client", 1)}, receive, send)
        assert sent[0]["status"] == 413

    asyncio.run(scenario())
    with TestClient(create_app()) as client:
        assert client.post("/api/polls", content=b"x" * 65537).status_code == 413


def test_websocket_origins_rate_and_cleanup(monkeypatch):
    """Verifica rechazo de orígenes, límite de aperturas y recuperación del cupo simultáneo."""
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
            # TestClient admite denegaciones HTTP y cierres previos a la aceptación.
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
