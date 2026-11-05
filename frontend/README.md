# VoteStupid frontend

Vue 3, TypeScript, Vite, and Vue Router. The interface is in Spanish; code comments and documentation are in English.

Use Node 24. From this directory:

```sh
npm ci
npm test
npm run build
npm run dev
```

For development, copy `.env.example` to a private `.env.development` and use `VITE_API_URL=http://localhost:8000`. Configure the backend to allow `http://localhost:5173`. Do not mix localhost and 127.0.0.1 when using cookies.

The Docker build sets an empty API base URL. HTTP requests use relative `/api/` paths and WebSockets derive ws/wss from the page origin. Nginx serves the production bundle and proxies both protocols.

Public routes: `/`, `/votaciones`, `/votacion/:id`. Private routes: `/admin`, `/admin/crear`, `/admin/:id`. Login: `/acceso`. Legacy `/crear` and `/historial` redirect to current routes.

Tests exercise real service/view logic using controlled transports and Vue lifecycle hooks. Run keyboard, mobile, and multi-device acceptance checks as described in [release validation](../docs/release-validation.md).

See the [root README](../README.md) for installation, Docker, publication, and backup instructions.
