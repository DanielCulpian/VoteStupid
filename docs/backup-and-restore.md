# PostgreSQL backup and safe restoration

## What must be protected

The external Docker volume contains polls, votes, results, session hashes, and schema state. Archives and manifests belong under the ignored `backups/` directory and are excluded from images. Do not commit, upload, or distribute them.

Keep a separate secured copy of your private configuration. The database archive does not contain the original administrator password or its environment configuration. Restore only archives you trust: PostgreSQL archives can contain executable SQL.

The maintenance utility uses Docker's PostgreSQL 17 clients, preserves binary data on Windows, and needs only Python's standard library on the host. It never uses `DROP`, `--clean`, or volume deletion.

## Create and verify a backup

Pause writes for the fingerprint comparison: stop the public connector, frontend, and backend, then start only PostgreSQL. On Windows:

```powershell
.\scripts\docker.ps1 stop
docker compose up -d --wait db
python scripts/database_backup.py backup --file backups/manual.dump
python scripts/database_backup.py verify --file backups/manual.dump
```

Use a new filename each time; existing archives and manifests are never overwritten. The first command creates a custom-format dump plus `manual.dump.json`, containing table row counts and hashes.

Verification creates a new database named `votestupid_restore_<random>`, restores the archive in one transaction, and compares the ordered contents of every public table with the manifest. The original database is unchanged. The validation database is retained for inspection; it is never used by the app and must not be selected as a regression-test database.

A successful dump alone is not proof of recoverability. Keep the archive and its manifest together, verify regularly, and store an encrypted offline copy on a separate device. Do not use filesystem copies of a running PostgreSQL data directory as a replacement for a logical backup.

Restart locally with `scripts/docker.ps1 start`, or publish a new temporary link with `scripts/tunnel.ps1 start -Mode temporary`.

## Recover without destroying the current volume

Recovery uses a **new empty volume**, retaining the original as a rollback point.

1. Stop the app and tunnel. Record the current volume name:

   ```powershell
   .\scripts\docker.ps1 stop
   docker inspect --format '{{range .Mounts}}{{.Name}} {{.Destination}}{{end}}' votestupid-db
   ```

2. Choose a new unique recovery volume. Do not reuse a name without inspecting it:

   ```powershell
   docker volume create votestupid_recovery_YYYYMMDD
   $env:POSTGRES_VOLUME_NAME = 'votestupid_recovery_YYYYMMDD'
   docker compose up -d --wait db
   ```

   On Linux use `export POSTGRES_VOLUME_NAME=votestupid_recovery_YYYYMMDD`. Use the same PostgreSQL credentials as the private configuration. Do not start the backend yet: migrations would make the destination nonempty.

3. Restore:

   ```powershell
   python scripts/database_backup.py restore-empty --file backups/manual.dump
   ```

   The utility refuses any destination with existing public tables, including a migrated database with zero polls. It does not overwrite an existing database.

4. Start and inspect the recovered app:

   ```powershell
   .\scripts\docker.ps1 start
   ```

   Check poll counts, representative results, administration, and WebSocket updates. Keep the original volume untouched. After confirming recovery, set the new `POSTGRES_VOLUME_NAME` in the private `.env` so later terminals use the intended volume. Consider rotating the administrator password to invalidate restored sessions.

5. If recovery fails, stop the app, restore the previous volume setting, and start again. Do not delete either volume during diagnosis.

On Linux the maintenance Python commands are identical. Use the equivalent Compose commands in the local operations guide when PowerShell is unavailable.

## Failure handling

A failed backup may leave a partial archive without a manifest. Retain it for diagnosis and choose a different filename for another attempt; do not treat it as a verified backup. If data changes during the manifest comparison, pause writes and repeat.

Restore verification requires PostgreSQL to be running, sufficient disk space for another database, and a readable archive/manifest pair. An invalid archive aborts restoration; inspect the isolated validation database, not production.

References: [PostgreSQL pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html) and [pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html).
