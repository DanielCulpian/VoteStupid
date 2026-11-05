"""Create private PostgreSQL archives and restore them without overwriting data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CONTAINER = 'votestupid-db'
DATABASE = 'votestupid'


def docker_executable():
    """Find Docker on PATH or in the standard per-user Windows installation."""
    command = shutil.which('docker')
    if command:
        return command
    candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/DockerDesktop/resources/bin/docker.exe'
    if candidate.is_file():
        return str(candidate)
    raise RuntimeError('Docker was not found. Install and start Docker Desktop or Docker Engine.')


def run_database(arguments, **kwargs):
    """Run a PostgreSQL client inside the container without exposing credentials."""
    command = [docker_executable(), 'exec', '-i', CONTAINER, *arguments]
    result = subprocess.run(command, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        raise RuntimeError('PostgreSQL command failed. The existing database was not replaced.')
    return result


def query(database, sql):
    """Return unformatted query output without printing database rows."""
    return run_database(['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-U', 'votestupid',
                         '-d', database, '-Atq', '-c', sql], stdout=subprocess.PIPE).stdout


def fingerprint(database):
    """Hash ordered table rows to compare a restored database without revealing its data."""
    tables = query(database, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").decode().splitlines()
    result = {}
    for table in tables:
        quoted = '"' + table.replace('"', '""') + '"'
        rows = query(database, f'SELECT row_to_json(t)::text FROM public.{quoted} t ORDER BY 1')
        result[table] = {'rows': len(rows.splitlines()), 'sha256': hashlib.sha256(rows).hexdigest()}
    return result


def private_path(value):
    """Keep archives under the repository's ignored backups directory."""
    path = (ROOT / value).resolve()
    if not path.is_relative_to((ROOT / 'backups').resolve()):
        raise ValueError('Use a path inside backups/ so database archives stay outside Git and images.')
    return path


def backup(path):
    """Write a custom-format archive and a manifest, refusing to overwrite existing files."""
    path = private_path(path)
    manifest = path.with_suffix(path.suffix + '.json')
    if path.exists() or manifest.exists():
        raise ValueError('The archive or its manifest already exists. Choose a new filename.')
    path.parent.mkdir(parents=True, exist_ok=True)
    before = fingerprint(DATABASE)
    with path.open('xb') as output:
        run_database(['pg_dump', '-U', 'votestupid', '-d', DATABASE, '--format=custom'], stdout=output)
    if fingerprint(DATABASE) != before:
        raise RuntimeError('Data changed during verification. The archive is retained; pause writes and create another backup.')
    with manifest.open('x', encoding='utf-8') as output:
        json.dump({'tables': before, 'created_at': datetime.now(timezone.utc).isoformat()}, output, indent=2)
    print(f'Archive created: {path.relative_to(ROOT)}')
    return path


def restore(path, database):
    """Restore only into a database without public tables, never using DROP or --clean."""
    if fingerprint(database):
        raise ValueError('Restore refused: the target database is not empty.')
    with path.open('rb') as archive:
        run_database(['pg_restore', '--exit-on-error', '--single-transaction', '--no-owner',
                      '--no-privileges', '-U', 'votestupid', '-d', database], stdin=archive)


def verify(path):
    """Restore the archive into a newly created validation database and compare every table."""
    path = private_path(path)
    manifest = json.loads(path.with_suffix(path.suffix + '.json').read_text(encoding='utf-8'))
    target = 'votestupid_restore_' + uuid4().hex[:12]
    run_database(['createdb', '-U', 'votestupid', '-T', 'template0', target])
    restore(path, target)
    if fingerprint(target) != manifest['tables']:
        raise RuntimeError('Restore validation failed: table fingerprints do not match the backup manifest.')
    print(f'Restore verified: {target}. Original database unchanged; validation database retained.')
    return target


def main():
    """Expose backup, validation, and guarded empty-database restoration commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'verify', 'restore-empty'])
    parser.add_argument('--file', required=True, help='Archive path inside backups/.')
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            backup(args.file)
        elif args.action == 'verify':
            verify(args.file)
        else:
            restore(private_path(args.file), DATABASE)
            print('Archive restored into the empty database. Existing populated databases are never overwritten.')
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
