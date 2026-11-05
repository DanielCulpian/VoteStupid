# HTTPS publication with Cloudflare Tunnel

## Free temporary publication

Quick Tunnels publish the local Nginx service through a temporary HTTPS hostname. No account, domain, router port forwarding, or permanent external server is needed. Data remains in the local PostgreSQL volume.

From the root on Windows:

```powershell
.\scripts\tunnel.ps1 start -Mode temporary
.\scripts\tunnel.ps1 url
.\scripts\tunnel.ps1 status
.\scripts\tunnel.ps1 logs
.\scripts\tunnel.ps1 stop
```

Start waits for the app and a registered Cloudflare connection, then configures the exact generated origin. Stop disconnects the tunnel before stopping the app. Ctrl+C only exits log following. The connector does not restart automatically with Docker.

Share the printed HTTPS URL. It changes when another Quick Tunnel is created, and browser sessions do not transfer between different hostnames. `url` shows the most recently generated address; `status` indicates whether the connector is running.

Quick Tunnels have no uptime guarantee, are intended for testing and temporary use, and allow at most 200 concurrent in-flight requests. They do not support SSE; VoteStupid uses WebSockets.

## Stable hostname with an owned domain

Adding a domain to the Cloudflare dashboard does not register it or establish ownership. Only configure hostnames under a domain you own and control.

If you already own a domain managed by Cloudflare:

1. Create a dedicated cloudflared tunnel in **Networking → Tunnels**.
2. Select Docker and copy only the token from the provided command into the private `.env` as `CLOUDFLARE_TUNNEL_TOKEN`. Do not execute that installation command or share the token.
3. Run:

   ```powershell
   .\scripts\tunnel.ps1 start -Hostname vote.your-domain.example
   ```

4. In the tunnel, add a **Published application route** with your chosen hostname, an empty path, type **HTTP**, and service **frontend:8080**. Do not use localhost inside the connector.
5. Confirm the public HTTPS page works. Do not overwrite DNS records used by another service.

A single-level subdomain normally uses the zone's universal certificate. Domain registration is separate from the free connector. No domain purchase is required for temporary URLs.

## Linux and manual operation

The Compose files work with Linux containers. The PowerShell helpers require `pwsh` on Linux; alternatively use Compose directly.

For a Quick Tunnel, create the private generated settings:

```sh
printf '%s\n' 'DOCKER_PUBLIC_ORIGIN=https://unconfigured.invalid' > .env.tunnel
docker compose --env-file .env --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml up -d --build --wait db backend frontend
docker compose --env-file .env --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml up -d --no-deps cloudflared
docker compose --env-file .env --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml logs --tail 100 cloudflared
```

Take the exact HTTPS URL from the connector logs, replace the origin in `.env.tunnel`, and run the first `up` command again so the backend accepts the new origin. Do not edit the main password configuration. Stop using the same Compose files with `stop`.

For a named tunnel, set the exact owned HTTPS origin first and append `-f compose.tunnel.named.yaml` to the Compose commands; the private `.env` must contain its token.

## Security and troubleshooting

- Only Nginx is connected to the tunnel network. The connector cannot resolve the private database/API services.
- Nginx trusts visitor IP headers only from the connector at 172.30.79.20, preserving per-visitor limits. Local clients cannot spoof that source.
- HTTP received from the connector is redirected to HTTPS. Backend cookies are always Secure in public mode and CORS uses one exact origin.
- Uvicorn trusts only Nginx's application-network IP. Ports 5432 and 8000 are never published by the normal stack.
- The connector uses a separate outbound network and HTTP/2 on TCP 7844. No inbound router port is needed.
- Do not override `Cache-Control: no-store` for `/api/` with Cloudflare cache rules.
- The fixed tunnel subnet is 172.30.79.0/24. Change both Compose and Nginx's trusted connector IP if it conflicts with another network; do not broaden trust.
- A failed helper startup attempts to stop the connector. Inspect `status` if Docker itself is unavailable.
- To return to local HTTP, use `scripts/docker.ps1 start`, which first disconnects the tunnel.
- Quick mode does not receive the optional named-tunnel token. Tokens and generated origin files remain excluded from Git and images.

## External-device acceptance

Turn off the phone's Wi-Fi and use mobile data. Check filters; all three vote types and vote changes; administrator HTTPS login, creation, closing/reopening; live updates in a second browser/device; and denial of private routes in a signed-out window.

After stopping the tunnel, refresh externally: the app must stop responding, usually with a Cloudflare error. Restart and verify saved polls and results. This mobile-data check cannot be replaced by a request from the host PC.

References: [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/), [named tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/), and [Cloudflare headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/).
