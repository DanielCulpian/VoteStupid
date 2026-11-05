# Architecture

## Runtime

A browser reaches Nginx, which serves Vue and proxies `/api/` HTTP and WebSocket traffic. FastAPI uses SQLAlchemy and psycopg to access PostgreSQL 17. Alembic upgrades the schema before the API starts.

Cloudflare Tunnel is optional and explicitly enabled. Its connector reaches Nginx on a dedicated network and Cloudflare on a separate outbound network. It cannot access the database/API network.

## Backend layers

- `backend/app/domain/`: poll, option, and vote entities; voting rules; repository contracts.
- `backend/app/application/`: creation, voting, updates, results, closing/reopening use cases and DTOs.
- `backend/app/infrastructure/`: SQLAlchemy models, mappings and repositories, security, sessions, WebSocket registry, and migrations.
- `backend/app/presentation/api/`: schemas, dependencies, HTTP routes, authentication routes, and WebSocket endpoints.

The domain is independent of FastAPI and SQLAlchemy. Infrastructure maps persistence models to domain entities. API dependencies construct use cases and enforce authorization.

## Frontend

`frontend/src/views/` contains public, participant, login, creation, and administration views. `services/` handles HTTP, voter tokens, authentication, catalog queries, and reconnection. `components/` shares catalog cards, connection notices, and live announcements. Vue Router guards private pages; the API independently checks every private operation.

One catalog subscription refreshes listings after public state changes. Individual poll subscriptions receive `results_updated` and `poll_status_updated`. Reconnection uses progressive delays, restores current HTTP snapshots, and cancels timers/transports when views unmount.

## Persistence and identity

Polls, options, votes, ordered selections, and administrator sessions live in PostgreSQL. Alembic manages schema revisions without startup sample data. External Docker volumes are runtime data, never image or Git content.

Participants have per-poll random browser tokens; only hashes reach persistence. An administrator password hash stays in private environment configuration. Random session cookies are stored as hashes with an expiration and credential version.

The public catalog exposes poll metadata and aggregate results, not administrative credentials. Administrator sessions recover access to earlier polls without retaining individual secret links.

## Tests and conventions

`tests/unit/` covers domain, application, schema, security, transport, and maintenance logic. `tests/integration/` exercises SQLAlchemy and FastAPI with PostgreSQL. The isolated database `votestupid_test` is required; fixtures must never target the application database.

`frontend/tests/` uses Node's test runner with real service/view logic and controlled dependencies. TypeScript checking is part of `npm run build`.

Python uses four-space indentation and snake_case; TypeScript/Vue uses two spaces, single quotes, and PascalCase components. Every function or method has an English purpose comment or docstring. Interface text remains Spanish.

## Operational boundaries

Use one API worker. In-memory rate limits and WebSocket connections are not shared across processes. Anonymous voting relies on trusted participants, and shared IPs share traffic quotas. See [security](api-security.md) and [release validation](release-validation.md).
