# Security and operating limits

## Intended use

VoteStupid supports temporary anonymous polls for trusted groups. There are no participant accounts. A browser-local voter token identifies a vote; users can create another identity by clearing storage or using another profile. This is not an identity-verified election system.

The catalog, individual polls, and aggregate results are public. Creation and every administrative API operation require the administrator session. Legacy individual poll tokens are checked when supplied but cannot replace that session.

## Credentials and sessions

The administrator password is stored only as a salted scrypt hash in the private configuration. Sessions contain random secrets in HttpOnly, SameSite Strict cookies scoped to `/api`; PostgreSQL stores only their hashes and credential version. Sessions expire after eight hours. Logout revokes the session; changing the password invalidates sessions associated with the previous hash.

Cookies default to Secure. Only local HTTP development may explicitly set `ADMIN_COOKIE_SECURE=false`. Tunnel mode forces it to true. Keep the same hostname for frontend and API when using SameSite cookies.

Administrative writes require `X-Requested-With: VoteStupid` and reject a supplied Origin unless it exactly matches the configured list. There are no wildcard origins. Frontend route guards improve navigation; backend authorization remains authoritative.

Voter and administration tokens are hashed before persistence. Original per-poll administration tokens are returned only by the authorized creation endpoint. Public responses do not include them. The frontend does not persist new administrative tokens.

## Input and traffic limits

Titles and option text allow 1–255 characters; descriptions allow at most 5,000. A poll has 2–50 options, and a vote contains at most 50 option identifiers. Inputs are trimmed; extra fields, empty values, duplicate selections, foreign options, invalid UUIDs, and dates without time zones are rejected.

HTTP bodies are limited to 64 KiB, including chunked requests. Invalid input receives 422; oversized bodies receive 413. Closing deadlines are enforced by the backend even if a client has stale state.

| Operation | Requests per minute per IP |
| --- | ---: |
| Login attempts | 5 |
| Poll creation | 10 |
| Vote creation and modification combined | 30 |
| Administrative operations combined | 30 |
| WebSocket openings | 30 |
| All HTTP and WebSocket traffic combined | 300 |

Login additionally has a global limit of 20 attempts per minute per process. Excess requests receive 429 and Retry-After. At most 20 simultaneous sockets per IP and 1,000 per process are allowed. Shared households/carrier NATs share limits.

Counters are bounded, in memory, and reset when the process restarts. Use **one API worker**: multiple processes would have independent quotas and WebSocket registries. Scaling requires coordinated limits and event delivery; no external paid service or Redis is required for this release.

## Errors, logs, and proxies

Validation responses omit original input and internal validator context. Internal errors return generic messages. Access logs omit query strings; never add logs for passwords, authentication headers, cookies, request bodies, or SQL parameters.

API responses use Cache-Control: no-store. Preserve it at Nginx and Cloudflare. WebSockets publish only results and state; client write messages are rejected.

The local proxy overwrites forwarded IP headers; Uvicorn trusts only Nginx's explicit internal IP. Tunnel traffic is trusted only from the dedicated connector address, using Cloudflare's visitor IP header. Spoofed headers received from local clients do not establish proxy trust.

Do not publish PostgreSQL or FastAPI, enable wildcard proxy trust, expose the development database override, or add other private tunnel routes.

## Private files and backup handling

Keep `.env`, all generated `.env.*` files, `.tunnel-url`, database archives, manifests, and the user's local launcher files outside Git and build contexts. The example environment files contain no usable credentials.

Backups include votes, poll token hashes, voter hashes, and session records. Treat them as private data. Keep a separate secured copy of the configuration for recovery. Only restore trusted archives; database archives can contain executable SQL.

A fresh clone and fresh volume must produce an empty catalog. Tests contain sample fixtures, but startup does not import them. Read [backup and restore](backup-and-restore.md) before recovering data.

## Known constraints

Quick Tunnel hostnames change, depend on the PC and network remaining online, and have no availability guarantee. Browser storage is required to remember voter identity. Automated accessibility checks supplement rather than replace keyboard and screen-reader checks. Physical reboot and mobile-network acceptance require an operator to perform them.

References: [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/), [Nginx WebSockets](https://nginx.org/en/docs/http/websocket.html), and [Uvicorn trusted proxies](https://www.uvicorn.org/settings/#http).
