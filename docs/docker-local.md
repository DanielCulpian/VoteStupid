# Ejecución local con Docker

## Configuración inicial

Inicia Docker Desktop. Desde la raíz, conserva tu `.env` privado con
`POSTGRES_PASSWORD` y `ADMIN_PASSWORD_HASH` ya configurados. Para HTTP local,
`ADMIN_COOKIE_SECURE=false`; para HTTPS debe ser `true`.
No copies contraseñas a `.env.example` ni publiques el resultado de `docker compose config`.

El acceso predeterminado es **http://localhost:8080**; la administración está en
**http://localhost:8080/acceso**. No necesitas iniciar Python, Node ni Vite en el host.

La configuración reutiliza **`votestupid_postgres_data`**, comprobado en este PC.
Es un volumen externo: Compose falla si no existe, en lugar de crear silenciosamente
una base vacía. Antes de cambiar de PC o carpeta, verifica:

```powershell
docker inspect --format '{{range .Mounts}}{{.Name}} {{.Destination}}{{end}}' votestupid-db
docker volume inspect votestupid_postgres_data
```

En una instalación nueva, sin datos anteriores, crea explícitamente ese volumen
con `docker volume create votestupid_postgres_data`. En una instalación existente
con otro volumen, configura `POSTGRES_VOLUME_NAME` con su nombre real. No cambies
la contraseña de PostgreSQL en `.env` esperando que cambie la de una base ya creada.

## Arranque, apagado y logs en Windows

```powershell
.\scripts\docker.ps1 start
.\scripts\docker.ps1 status
.\scripts\docker.ps1 logs
.\scripts\docker.ps1 stop
```

`start` construye las imágenes y espera la salud de los servicios. `logs` sigue
los últimos mensajes; Ctrl+C sale del seguimiento. `stop` detiene los contenedores
y conserva el volumen. Estos comandos no modifican tus tres archivos locales.

Equivalentes desde la raíz:

```powershell
docker compose up -d --build --wait --wait-timeout 180
docker compose ps -a
docker compose logs --tail 100 -f
docker compose stop
```

No ejecutes `docker compose down -v` ni elimines volúmenes. La copia SQL previa
a esta tarea está en `backups/before-docker-task11.sql`, excluida de Git.

## Servicios y migraciones

- Nginx sin privilegios sirve Vue compilado y reenvía `/api/`, incluidos los
  WebSockets. El único puerto publicado es `127.0.0.1:8080`.
- FastAPI funciona sin privilegios, con sistema de archivos de solo lectura y
  un único worker para compartir correctamente rate limiting y conexiones.
- PostgreSQL 17 conserva los datos en el volumen existente y no publica puerto.
- El backend espera a PostgreSQL, aplica `alembic upgrade head` y arranca Uvicorn.
  Una migración fallida impide iniciar la API. No se borran ni recrean tablas.
- Los healthchecks comprueban PostgreSQL, una lectura real de la API y Nginx.
  Si falla el arranque, consulta `docker compose logs --tail 100 backend`.

Vue utiliza el mismo origen para HTTP y WebSocket; no contiene secretos ni una URL
del backend incrustada. Nginx sustituye las cabeceras de IP reenviada y Uvicorn
confía solo en su IP interna. Los logs de Nginx omiten query y credenciales.

Si el puerto está ocupado, cambia conjuntamente `HTTP_PORT` y
`DOCKER_PUBLIC_ORIGIN`. Usa el origen exacto con el que accedes, sin barra final.
Si la subred colisiona con otra red, cambia `DOCKER_INTERNAL_SUBNET` y
`NGINX_INTERNAL_IP` por una dirección libre perteneciente a ella.
No añadas `--forwarded-allow-ips=*` ni publiques los puertos internos.

Esta configuración es para HTTP local. Antes de añadir Cloudflare/Nginx externo,
adapta HTTPS, origen público, cookie Secure y proxies de confianza; no basta con
cambiar el puerto. Las sesiones y credenciales nunca deben cachearse en el proxy.

## Desarrollo fuera de Docker

Para ejecutar pytest o FastAPI desde Windows, publica PostgreSQL explícitamente
solo en loopback mediante el archivo opcional:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d db
$env:PYTHONPATH = 'backend'
python -m pytest -v
```

Las pruebas de integración usan `votestupid_test`, que debe existir; nunca apuntes
las fixtures a la base real. Para volver al conjunto aislado, ejecuta el arranque
normal: Compose retirará el puerto añadido. En `frontend/`, usa `npm test` y
`npm run build` para las comprobaciones locales.

Referencias: [orden de arranque de Compose](https://docs.docker.com/compose/how-tos/startup-order/)
y [proxy WebSocket de Nginx](https://nginx.org/en/docs/http/websocket.html).

## Validación de esta tarea

- Imágenes construidas y los tres contenedores saludables; Alembic completado.
- Volumen original conservado: 30 votaciones y 24 votos antes de las pruebas.
- Tres votaciones nuevas de prueba, una por tipo, con voto anónimo, filtros
  combinados, resultados y eventos de cierre/reapertura a través de Nginx.
- Reinicio completo comprobado: catálogo y resultados idénticos y la sesión
  administrativa anterior al reinicio continúa siendo válida.
- Portada servida por Nginx comprobada en navegador. El control del navegador
  fue detenido por el usuario antes de completar el login y creación visuales;
  esos flujos sí pasaron mediante peticiones reales a través del proxy.
- Backend: **197 tests superados**. Frontend: **39 tests superados** y build correcto,
  tanto en el host como durante la construcción de la imagen.
- Corregido el acceso del archivo opcional de desarrollo: necesita conectar la
  base a la red no aislada además de publicar 5432 únicamente en loopback.

Las credenciales temporales utilizadas en las pruebas no se guardan en el `.env`.
Antes de entregar se restaura la configuración administrativa original y se retira
el puerto opcional de PostgreSQL. No se han modificado los tres scripts/textos
locales del usuario ni se han hecho commits o push.
