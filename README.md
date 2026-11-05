# VoteStupid

VoteStupid is a self-hosted voting app for friends. Visitors vote anonymously without accounts; one password protects the private administration area. The interface is in Spanish; source documentation and guides are in English.

## Features

- Single-choice, multiple-choice, and ranking polls, including vote changes.
- Public home page and catalog with combined state/type filters.
- Live results, closing/reopening, and automatic WebSocket reconnection.
- Private creation and administration, eight-hour sessions, and access to previous polls.
- Persistent PostgreSQL storage, Docker Compose, Nginx, and optional HTTPS publication through Cloudflare Tunnel.

Ranking uses Borda points: with N options, first place receives N−1 points and last place receives zero. Choice percentages use the number of voters, so multiple-choice percentages can add up to more than 100%.

## First installation

Requirements: Docker Desktop with Linux containers on Windows, or Docker Engine with Compose v2 on Linux. Python 3.14 is used for the setup and backup utilities; Node 24 is needed only for frontend development. Runtime services run entirely in containers.

1. Copy the example configuration. **Keep an existing private configuration and volume if you are upgrading.**

   ```powershell
   Copy-Item .env.example .env
   ```

   On Linux, use `cp .env.example .env`. In the private file, set a strong `POSTGRES_PASSWORD`. Never commit this file.

2. Create a Python environment and configure the administrator password:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python scripts/configure_admin.py --write-env --local-http
   ```

   On Linux activate it with `source .venv/bin/activate`. The password must contain 16–256 characters. Only its scrypt hash is stored. There is no default administrator password.

   For Docker-only password generation, build the backend image and run the configurator interactively:

   ```powershell
   docker build -f backend/Dockerfile -t votestupid-backend .
   docker run --rm -it --entrypoint python votestupid-backend scripts/configure_admin.py
   ```

   Copy the resulting hash into your private `.env`, enclosed in **single quotes** so Compose preserves dollar signs, and set `ADMIN_COOKIE_SECURE=false` for local HTTP only.

3. On a **new installation with no existing data**, create an empty volume:

   ```powershell
   docker volume create votestupid_postgres_data
   ```

   Before reusing a machine or changing the volume name, read [storage and startup](docs/docker-local.md). A clone contains no polls, votes, sessions, database dumps, or database volume. Migrations create the schema without seeding polls.

4. Start the app:

   ```powershell
   .\scripts\docker.ps1 start
   ```

   Open **http://localhost:8080**. Administration: **http://localhost:8080/acceso**.

## Daily operation

```powershell
.\scripts\docker.ps1 status
.\scripts\docker.ps1 logs
.\scripts\docker.ps1 stop
```

On Linux, or without PowerShell, use:

```sh
docker compose up -d --build --wait --wait-timeout 180
docker compose ps -a
docker compose logs --tail 100 -f
docker compose stop
```

Stop preserves data. Never remove the PostgreSQL volume or run `docker compose down -v`. Closing a logs window does not stop the app.

Create polls from the private dashboard. Share public poll links with participants. Use the same browser profile to change a vote: its voter token is stored locally. Clearing browser storage loses that identity. Anonymous voting does not guarantee one vote per human; this app is intended for trusted groups.

## Publish temporarily over HTTPS

No account, domain purchase, router changes, or permanent external server is required:

```powershell
.\scripts\tunnel.ps1 start -Mode temporary
.\scripts\tunnel.ps1 url
.\scripts\tunnel.ps1 stop
```

Share the printed HTTPS URL. Each new Quick Tunnel has a different hostname. Public mode forces Secure cookies and the exact allowed origin. Use that HTTPS address for administration, not local HTTP.

See [Cloudflare Tunnel](docs/cloudflare-tunnel.md) for stable-domain setup and the Linux commands. Adding a domain to Cloudflare does not register or purchase it.

## Maintenance and development

- [Backups and safe restoration](docs/backup-and-restore.md)
- [Architecture and repository layout](docs/architecture.md)
- [Security and operating limits](docs/api-security.md)
- [Release validation and remaining checks](docs/release-validation.md)

Backend checks, with a separate `votestupid_test` database:

```powershell
python -m pip install pytest httpx
docker compose -f compose.yaml -f compose.dev.yaml up -d --wait db
$env:PYTHONPATH = 'backend'
python -m pytest -v
```

Configure a private host `DATABASE_URL` first. See the development guide in [Docker local](docs/docker-local.md) for creating the test database. Integration fixtures create and drop tables only in that database.

Frontend checks, from `frontend/`:

```sh
npm ci
npm test
npm run build
```

## Troubleshooting

- **Docker cannot connect:** start Docker Desktop and wait for its engine.
- **External volume not found:** identify the old volume before creating anything; do not replace existing data with an empty volume.
- **Login fails over local HTTP:** use local mode, `ADMIN_COOKIE_SECURE=false`, and the same hostname for frontend/API.
- **Public login or WebSocket fails:** use the latest tunnel URL and check `scripts/tunnel.ps1 logs`; the previous URL may be obsolete.
- **Migration/startup fails:** inspect `docker compose logs --tail 100 backend`. Do not reset the database.
- **HTTP 429:** wait for the rate-limit window to expire.
- **Port or subnet conflict:** adjust the documented port/origin or subnet/proxy IP together.
- **Need recovery:** restore into a new empty target and validate it before switching; retain the original volume.

No release tag or GitHub publication should be made until the release checklist is complete.
