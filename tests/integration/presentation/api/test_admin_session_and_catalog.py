from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.infrastructure.security.admin_session import COOKIE_NAME, password_hash, session_db, session_hash
from app.infrastructure.models.admin_session_model import AdminSessionModel
from app.infrastructure.repositories.sqlalchemy_poll_repository import SqlAlchemyPollRepository
from app.presentation.api.dependencies import get_poll_repository

PASSWORD = "test-only-long-password-for-administration"
HASH = password_hash(PASSWORD)
HEADERS = {"X-Requested-With": "VoteStupid", "Origin": "http://localhost:5173"}


@pytest.fixture
def private_client(db_session, monkeypatch):
    """Ejecuta la autenticación real contra PostgreSQL sin sustituir sus controles de acceso."""
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", HASH)
    monkeypatch.setenv("ADMIN_COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    app = create_app()
    app.dependency_overrides[session_db] = lambda: db_session
    app.dependency_overrides[get_poll_repository] = lambda: SqlAlchemyPollRepository(db_session)
    with TestClient(app, headers=HEADERS) as client:
        yield client, db_session


def sign_in(client):
    """Autentica al administrador mediante el endpoint real y su cookie."""
    response = client.post("/api/admin/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200
    return response


def create(client, kind="single_choice", **extra):
    """Crea una votación mediante una sesión administrativa válida."""
    response = client.post("/api/polls", json={"title": "Catálogo privado", "poll_type": kind, "option_texts": ["A", "B"], **extra})
    assert response.status_code == 201
    return response.json()


def test_visitors_cannot_create_or_manage_even_with_individual_token(private_client):
    """Rechaza peticiones directas sin sesión y permite seguir consultando y votando."""
    client, _ = private_client
    assert client.post("/api/polls", json={}).status_code == 401
    assert client.get("/api/admin/polls").status_code == 401
    sign_in(client)
    poll = create(client)
    client.delete("/api/admin/auth/session")
    for method, suffix in [("get", ""), ("put", "/close"), ("put", "/reopen")]:
        response = getattr(client, method)(f"/api/admin/polls/{poll['id']}{suffix}", headers={"X-Admin-Token": poll["admin_token"]})
        assert response.status_code == 401
    assert client.get(f"/api/polls/{poll['id']}").status_code == 200
    assert client.post(f"/api/polls/{poll['id']}/votes", headers={"X-Voter-Token": "v" * 40},
                       json={"selected_option_ids": [poll["options"][0]["id"]]}).status_code == 201


def test_cookies_logout_expiry_rotation_and_old_polls(private_client, monkeypatch):
    """Comprueba cookies, revocación, caducidad y acceso recuperable sin el token individual."""
    client, db = private_client
    response = sign_in(client)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    token = client.cookies.get(COOKIE_NAME)
    assert token not in response.text
    poll = create(client)
    assert client.get(f"/api/admin/polls/{poll['id']}").status_code == 200
    assert client.put(f"/api/admin/polls/{poll['id']}/close").status_code == 200
    assert client.put(f"/api/admin/polls/{poll['id']}/reopen").status_code == 200
    session = db.get(AdminSessionModel, session_hash(token))
    assert session.token_hash != token
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/admin/auth/session").status_code == 401
    assert client.post("/api/polls", json={}).status_code == 401
    sign_in(client)
    assert client.get(f"/api/admin/polls/{poll['id']}").status_code == 200
    stolen = client.cookies.get(COOKIE_NAME)
    assert client.delete("/api/admin/auth/session").status_code == 200
    client.cookies.set(COOKIE_NAME, stolen)
    assert client.get("/api/admin/auth/session").status_code == 401
    client.cookies.clear()
    sign_in(client)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", HASH + "changed")
    assert client.get("/api/admin/auth/session").status_code == 401


def test_login_is_throttled_and_csrf_and_missing_configuration_fail_closed(private_client, monkeypatch):
    """Rechaza formularios ajenos y configuración ausente y limita intentos de contraseña."""
    client, _ = private_client
    assert client.post("/api/admin/auth/login", headers={"Origin": "https://evil.example"}, json={"password": PASSWORD}).status_code == 403
    monkeypatch.delenv("ADMIN_PASSWORD_HASH")
    assert client.post("/api/admin/auth/login", json={"password": PASSWORD}).status_code == 503
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", HASH)
    for _ in range(3):
        response = client.post("/api/admin/auth/login", json={"password": "incorrect-password"})
        assert response.status_code == 401
        assert "incorrect-password" not in response.text
    response = client.post("/api/admin/auth/login", json={"password": PASSWORD})
    assert response.status_code == 429
    assert response.headers["Retry-After"]


def test_catalog_filters_pagination_privacy_and_websocket(private_client):
    """Comprueba filtros combinados, paginación, cierres programados y avisos de catálogo."""
    client, _ = private_client
    sign_in(client)
    with client.websocket_connect("/api/polls/catalog/ws", headers={"Origin": "http://localhost:5173"}) as socket:
        single = create(client)
        assert socket.receive_json()["type"] == "poll_status_updated"
        multiple = create(client, "multiple_choice")
        socket.receive_json()
        ranking = create(client, "ranking", closes_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat())
        socket.receive_json()
        client.put(f"/api/admin/polls/{multiple['id']}/close")
        assert socket.receive_json()["is_active"] is False
        inactive = client.get("/api/polls?state=inactive&poll_type=multiple_choice&limit=100").json()
        assert multiple["id"] in [p["id"] for p in inactive["items"]]
        assert all(p["poll_type"] == "multiple_choice" and not p["is_active"] for p in inactive["items"])
        active = client.get("/api/polls?state=active&poll_type=ranking&limit=100").json()
        assert ranking["id"] not in [p["id"] for p in active["items"]]
        client.put(f"/api/admin/polls/{multiple['id']}/reopen")
        assert socket.receive_json()["is_active"] is True
        active = client.get("/api/polls?state=active&poll_type=multiple_choice&limit=100").json()
        assert multiple["id"] in [p["id"] for p in active["items"]]
    first = client.get("/api/polls?limit=1").json()
    second = client.get("/api/polls?limit=1&offset=1").json()
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get("/api/polls?state=invalid").status_code == 422
    assert client.get("/api/polls?limit=1000").status_code == 422
    for poll in [single, multiple, ranking]:
        assert poll["admin_token"] not in str(first)
    assert "token" not in str(first) and "options" not in str(first)


def test_secure_cookie_is_default_and_cannot_authorize_plain_http(private_client, monkeypatch):
    """Mantiene Secure por defecto y comprueba que el navegador no envía esa cookie por HTTP."""
    client, _ = private_client
    monkeypatch.delenv('ADMIN_COOKIE_SECURE')
    response = sign_in(client)
    assert 'Secure' in response.headers['set-cookie']
    assert 'HttpOnly' in response.headers['set-cookie']
    assert client.get('/api/admin/auth/session').status_code == 401


def test_same_site_without_custom_header_cannot_login_or_mutate(private_client):
    """Rechaza peticiones simples incluso cuando el origen coincide y existe una cookie válida."""
    client, _ = private_client
    client.headers.pop('X-Requested-With')
    assert client.post('/api/admin/auth/login', json={'password': PASSWORD}).status_code == 403
    client.headers['X-Requested-With'] = 'VoteStupid'
    sign_in(client)
    poll = create(client)
    client.headers.pop('X-Requested-With')
    assert client.put(f"/api/admin/polls/{poll['id']}/close").status_code == 403
    assert client.delete('/api/admin/auth/session').status_code == 403


def test_reopen_expired_poll_retires_deadline_and_allows_voting(private_client):
    """Reabrir una votación vencida debe permitir votar y coincidir en detalle y catálogo."""
    client, _ = private_client
    sign_in(client)
    poll = create(client, closes_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())
    assert poll['is_active'] is False
    assert client.get(f"/api/polls/{poll['id']}").json()['is_active'] is False
    reopened = client.put(f"/api/admin/polls/{poll['id']}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()['is_active'] is True and reopened.json()['closes_at'] is None
    assert client.post(f"/api/polls/{poll['id']}/votes", headers={'X-Voter-Token': 'z' * 40},
                       json={'selected_option_ids': [poll['options'][0]['id']]}).status_code == 201
