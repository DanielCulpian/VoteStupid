"""Test container startup without opening real connections or processes."""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url


def load_startup():
    """Load the entry point without executing it automatically."""
    path = Path(__file__).resolve().parents[3] / 'scripts' / 'container_start.py'
    spec = importlib.util.spec_from_file_location('container_start', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migrates_before_starting_and_encodes_database_password(monkeypatch):
    """Verify migrates before starting and encodes database password."""
    module = load_startup()
    calls = []
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://localhost/unused')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'test-only@password:%/$')
    monkeypatch.setenv('NGINX_INTERNAL_IP', '172.30.78.10')
    monkeypatch.setattr(module.command, 'upgrade', lambda config, revision: calls.append(revision))
    monkeypatch.setattr(module.os, 'execv', lambda executable, args: calls.append(args))
    module.main()
    url = make_url(module.os.environ['DATABASE_URL'])
    assert url.password == 'test-only@password:%/$'
    assert url.host == 'db' and url.database == 'votestupid'
    assert calls[0] == 'head'
    assert calls[1][-3:] == ['172.30.78.10', '--ws-max-size', '1024']
    assert calls[1][calls[1].index('--workers') + 1] == '1'


def test_failed_migration_prevents_server_start(monkeypatch):
    """Verify failed migration prevents server start."""
    module = load_startup()
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://localhost/unused')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'test-only-password')

    def fail_migration(config, revision):
        """Simulate a migration failure without accessing the database."""
        raise RuntimeError('migration failed')

    monkeypatch.setattr(module.command, 'upgrade', fail_migration)
    monkeypatch.setattr(module.os, 'execv', lambda *args: pytest.fail('No debe iniciar Uvicorn'))
    with pytest.raises(RuntimeError, match='migration failed'):
        module.main()
