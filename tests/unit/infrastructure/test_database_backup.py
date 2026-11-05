"""Protect existing databases and keep backup archives private and binary-safe."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def backup_tool(tmp_path, monkeypatch):
    """Load the maintenance CLI with an isolated output directory."""
    path = Path(__file__).resolve().parents[3] / 'scripts/database_backup.py'
    spec = importlib.util.spec_from_file_location('database_backup', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    return module


def test_backup_path_rejects_files_outside_ignored_directory(backup_tool):
    """Reject archive paths that could publish data or escape the workspace."""
    for value in ['public.dump', '../outside.dump', 'backups/../../outside.dump']:
        with pytest.raises(ValueError, match='backups/'):
            backup_tool.private_path(value)


def test_backup_refuses_to_overwrite_existing_archive(backup_tool):
    """Keep earlier backups intact when a filename is accidentally reused."""
    path = backup_tool.ROOT / 'backups/existing.dump'
    path.parent.mkdir()
    path.write_bytes(b'original')
    with pytest.raises(ValueError, match='already exists'):
        backup_tool.backup('backups/existing.dump')
    assert path.read_bytes() == b'original'


def test_backup_preserves_binary_archive_and_writes_manifest(backup_tool, monkeypatch):
    """Avoid PowerShell text encoding corruption when saving PostgreSQL archives."""
    expected = b'PGDMP\x00\xff\x01\r\n'
    tables = {'polls': {'rows': 2, 'sha256': 'test-digest'}}
    monkeypatch.setattr(backup_tool, 'fingerprint', lambda database: tables)

    def dump(arguments, **kwargs):
        """Write controlled binary content through the same output stream."""
        assert '--format=custom' in arguments
        kwargs['stdout'].write(expected)

    monkeypatch.setattr(backup_tool, 'run_database', dump)
    path = backup_tool.backup('backups/new.dump')
    assert path.read_bytes() == expected
    assert json.loads(path.with_suffix('.dump.json').read_text())['tables'] == tables


def test_restore_refuses_existing_database_before_running_commands(backup_tool, monkeypatch):
    """Never invoke pg_restore against a database that already contains tables."""
    monkeypatch.setattr(backup_tool, 'fingerprint', lambda database: {'polls': {'rows': 0}})
    monkeypatch.setattr(backup_tool, 'run_database', lambda *args, **kwargs: pytest.fail('Database must remain untouched'))
    with pytest.raises(ValueError, match='not empty'):
        backup_tool.restore(Path('unused.dump'), 'votestupid')


@pytest.mark.parametrize('matches', [True, False])
def test_verification_uses_new_database_and_checks_fingerprints(backup_tool, monkeypatch, matches):
    """Validate restores without reusing a production or regression-test database."""
    path = backup_tool.ROOT / 'backups/check.dump'
    path.parent.mkdir()
    path.with_suffix('.dump.json').write_text(json.dumps({'tables': {'polls': {'rows': 1}}}))
    calls = []
    monkeypatch.setattr(backup_tool, 'run_database', lambda arguments, **kwargs: calls.append(arguments))
    monkeypatch.setattr(backup_tool, 'restore', lambda archive, database: calls.append(database))
    monkeypatch.setattr(backup_tool, 'fingerprint', lambda database: {'polls': {'rows': 1 if matches else 2}})
    if matches:
        target = backup_tool.verify('backups/check.dump')
        assert target.startswith('votestupid_restore_')
        assert calls[0][-1] == target and calls[1] == target
    else:
        with pytest.raises(RuntimeError, match='do not match'):
            backup_tool.verify('backups/check.dump')
