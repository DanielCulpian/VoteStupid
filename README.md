# VoteStupid

Plataforma de votaciones anónimas de elección única, múltiple y ranking.
FastAPI, SQLAlchemy y PostgreSQL; Vue 3 y TypeScript; resultados y estado por WebSocket.

## Ejecutar con Docker en Windows

Con Docker Desktop iniciado y el `.env` privado configurado:

```powershell
.\scripts\docker.ps1 start
```

Abre **http://localhost:8080**. Para administrar, entra en **/acceso**.
La portada conserva la presentación y el catálogo público con filtros por estado
y tipo. Crear, cerrar y reabrir votaciones requiere sesión administrativa.

```powershell
.\scripts\docker.ps1 status
.\scripts\docker.ps1 logs
.\scripts\docker.ps1 stop
```

El apagado conserva las votaciones, votos y sesiones en el volumen externo
`votestupid_postgres_data`. Nginx es el único punto de acceso; PostgreSQL y
FastAPI no publican puertos. Las migraciones se aplican antes de arrancar la API.

Consulta [configuración, persistencia y resolución de problemas](docs/docker-local.md).
Nunca elimines el volumen ni ejecutes `docker compose down -v`.

## Configurar la administración

Para compartir VoteStupid por HTTPS con tu dominio o con una URL temporal gratuita,
consulta [Cloudflare Tunnel](docs/cloudflare-tunnel.md). La publicación se activa
explícitamente con `scripts/tunnel.ps1`; el arranque local no publica en Internet.

Con el entorno Python activado, desde la raíz:

```powershell
python scripts/configure_admin.py --write-env --local-http
```

Solicita una contraseña de 16–256 caracteres y guarda únicamente su hash scrypt
en el `.env` privado. No hay contraseña predeterminada. `--local-http` permite
cookies sin Secure para HTTP local; omítelo con HTTPS. Recrea el backend después
de cambiar la configuración: `docker compose up -d --wait`.

Las cookies son HttpOnly y SameSite Strict; las sesiones duran ocho horas y se
persisten mediante hash. La sesión permite recuperar votaciones anteriores sin
conservar enlaces secretos. Los participantes no necesitan cuentas. Los tokens
individuales antiguos también requieren sesión; el frontend no guarda nuevos
tokens administrativos en almacenamiento local.

## Desarrollo y pruebas

Instala las dependencias Python con `python -m pip install -r requirements.txt`;
para ejecutar las pruebas añade `python -m pip install pytest httpx`.
Configura `DATABASE_URL` en el `.env` privado para desarrollo desde el host.
Publica PostgreSQL solo en loopback con el archivo opcional:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d db
$env:PYTHONPATH = 'backend'
alembic upgrade head
python -m pytest -v
python -m uvicorn app.main:app --app-dir backend --reload
```

Las pruebas de integración requieren `votestupid_test` y crean y eliminan tablas
exclusivamente en esa base. El arranque Docker normal retira el puerto opcional.

Desde `frontend/`:

```powershell
npm ci
npm test
npm run build
npm run dev
```

Para Vite usa `http://localhost:5173` y `VITE_API_URL=http://localhost:8000`;
declara ese origen en `CORS_ALLOWED_ORIGINS`. No mezcles `localhost` y `127.0.0.1`
al usar cookies SameSite. Docker usa `DOCKER_PUBLIC_ORIGIN` y el mismo origen para
API y frontend, sin necesitar Vite ni Python instalados en el host.

Consulta [la guía de seguridad](docs/api-security.md). No publiques archivos de
entorno, copias SQL ni credenciales. El despliegue actual utiliza un único worker.
