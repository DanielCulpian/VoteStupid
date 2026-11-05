# VoteStupid

Plataforma de votaciones an?nimas de elecci?n ?nica, m?ltiple y ranking.
Backend FastAPI y PostgreSQL, frontend Vue 3 con TypeScript y resultados por WebSocket.

## Participar y administrar

`/` conserva la presentaci?n de VoteStupid e incorpora el cat?logo p?blico.
`/votaciones` permite filtrar por estado y tipo, combinar filtros y consultar
resultados. Las votaciones disponibles aparecen primero y las m?s recientes
encabezan cada grupo. `/historial` redirige al cat?logo.

La creaci?n y administraci?n requieren iniciar sesi?n en `/acceso`.
Desde `/admin` se pueden crear, consultar, cerrar y reabrir votaciones anteriores,
sin conservar manualmente un enlace secreto. La API comprueba la sesi?n incluso
en peticiones directas. Los participantes siguen votando sin cuentas.

## Desarrollo local

Instala las dependencias Python del proyecto en un entorno virtual y configura
el `.env` privado a partir de `.env.example`, incluyendo las conexiones PostgreSQL.
Desde la ra?z, con ese entorno activado:

```powershell
docker compose up -d db
alembic upgrade head
python scripts/configure_admin.py --write-env --local-http
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --app-dir backend --reload
```

El configurador solicita una contrase?a de 16?256 caracteres y guarda ?nicamente
su hash. No existe una contrase?a predeterminada. Reinicia el backend despu?s
de cambiarla; las sesiones anteriores dejar?n de ser v?lidas.

Desde `frontend/`:

```powershell
npm ci
npm run dev
```

Usa `http://localhost:5173` y `VITE_API_URL=http://localhost:8000`, como indica
`frontend/.env.example`. Mant?n el mismo hostname en frontend y API para que
funcionen las cookies SameSite; no mezcles `localhost` y `127.0.0.1`.

## Persistencia y seguridad

PostgreSQL conserva votaciones, votos y sesiones. El volumen `postgres_data`
persiste al detener y arrancar el contenedor; no uses `docker compose down -v`
si deseas conservar los datos. El cat?logo administrativo ya no depende del
almacenamiento local del navegador.

Las sesiones duran ocho horas y usan cookies HttpOnly, SameSite Strict y Secure
por defecto. `--local-http` permite HTTP ?nicamente para desarrollo. En producci?n
configura HTTPS y `ADMIN_COOKIE_SECURE=true`; no publiques el `.env`.
Los tokens individuales existentes siguen valid?ndose si se env?an, pero tambi?n
requieren sesi?n administrativa. El frontend no almacena nuevos tokens de administrador.

Consulta [la gu?a de seguridad](docs/api-security.md) para l?mites, CORS y proxies.
El despliegue actual requiere un ?nico worker y no utiliza servicios externos de pago.

## Comprobaciones

Desde la ra?z, con el entorno virtual activado:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest -v
```

Las pruebas de integraci?n necesitan la base `votestupid_test`; sus fixtures
crean y eliminan tablas exclusivamente en ella. Desde `frontend/`, ejecuta
`npm test` y `npm run build`. Comprueba adem?s los filtros, el acceso privado y
los eventos en directo desde navegador; consulta el [seguimiento](docs/public-hall-checkpoint.md).
