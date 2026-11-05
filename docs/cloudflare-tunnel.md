# Publicar VoteStupid con Cloudflare Tunnel

## Dirección estable con tu dominio

El modo elegido actualmente es **temporal gratuito**: el usuario solo había añadido
`votestupid.com` al panel de Cloudflare, sin registrar ese dominio. Añadir una zona
no otorga su propiedad; no se han modificado sus DNS ni contratado servicios.
Usa `scripts/tunnel.ps1 start -Mode temporary` y comparte la URL que devuelve.

Si en el futuro registras un dominio, podrás activar el modo estable. Para usar el dominio raíz,
deja el campo Subdomain vacío y selecciona `votestupid.com` como Domain. El comando
de arranque correspondiente es:

```powershell
.\scripts\tunnel.ps1 start -Hostname votestupid.com
```

El hostname `votestupid.com` no está publicado por este proyecto. Si ya existe un registro DNS para la raíz, comprueba
qué servicio utiliza antes de sustituirlo. Los ejemplos siguientes con subdominio
también sirven si prefieres conservar otro servicio en el dominio raíz.

Se reutiliza tu dominio existente en Cloudflare. No necesitas abrir puertos del
router, contratar un servidor ni comprar otro dominio. Usa un subdominio libre
de un nivel, por ejemplo `votestupid.tudominio.es`, para aprovechar el certificado
habitual de Cloudflare. No sobrescribas un registro DNS utilizado por otro servicio.

1. En tu cuenta de Cloudflare, abre **Networking → Tunnels → Create a tunnel**.
   Crea un túnel dedicado llamado `votestupid` y elige el conector `cloudflared`.
2. Selecciona Docker. Del comando mostrado, copia únicamente el valor que sigue
   a `--token` y guárdalo localmente en el `.env` privado:

   ```dotenv
   CLOUDFLARE_TUNNEL_TOKEN=valor_privado_del_token
   ```

   No envíes el token por chat, no lo guardes en `.env.example` y no ejecutes el
   comando de instalación: Compose se encarga del contenedor. Quien tenga el token
   puede conectar otro conector al túnel; si se filtra, rótalo en Cloudflare.
3. Desde la raíz, con Docker Desktop iniciado:

   ```powershell
   .\scripts\tunnel.ps1 start -Hostname votestupid.tudominio.es
   ```

4. En ese túnel, añade una **Published application route**:
   - Hostname: el subdominio elegido, por ejemplo `votestupid.tudominio.es`.
   - Path: vacío, para servir toda la aplicación.
   - Service: tipo **HTTP**, dirección **`frontend:8080`**.
   - No añadas rutas hacia PostgreSQL, FastAPI ni redes privadas.

   Cloudflare crea el registro DNS del hostname. No uses `localhost:8080`: dentro
   del conector apuntaría al propio contenedor, no a Nginx.
5. Abre `https://votestupid.tudominio.es`. El servicio interno es HTTP en una red
   Docker aislada; los visitantes usan HTTPS y el conector cifra la conexión con
   Cloudflare. Conserva la contraseña administrativa actual y entra en `/acceso`.

## Controlar la publicación

```powershell
.\scripts\tunnel.ps1 status
.\scripts\tunnel.ps1 logs
.\scripts\tunnel.ps1 url
.\scripts\tunnel.ps1 stop
```

`start` espera a los servicios y a que Cloudflare registre una conexión. Confirma
después el acceso por el hostname, ya que el DNS y la ruta se configuran en tu
cuenta. `stop` detiene primero el túnel y luego la aplicación, conservando el volumen.
El DNS puede seguir existiendo, pero no debe permitir acceder a VoteStupid apagado.
Ctrl+C termina únicamente el seguimiento de logs; **no detiene el túnel**.
`url` muestra la última dirección generada; consulta `status` para saber si sigue activo.

Para volver a HTTP local sin publicación, usa `scripts/docker.ps1 start`. Este
script detiene primero cualquier conector del proyecto y restaura las variables
locales del `.env`. El conector tiene `restart: "no"`: no publica automáticamente
al reiniciar Docker Desktop. Tras una suspensión o cambio de red, comprueba su estado.

El modo público genera `.env.tunnel` y `.tunnel-url`, excluidos de Git y de las
imágenes. No modifica tu contraseña ni el `.env` original. Fuerza cookie Secure y
un único origen HTTPS exacto. El login local por HTTP no debe usarse en ese modo.

## Alternativa gratuita sin dominio

```powershell
.\scripts\tunnel.ps1 start -Mode temporary
```

Genera una URL HTTPS `trycloudflare.com` sin cuenta ni token. Cambia al crear otro
túnel, no tiene garantía de disponibilidad y está pensada para pruebas, con un
límite de 200 peticiones simultáneas. El script configura el origen exacto recibido;
no utiliza un comodín CORS. Las sesiones del navegador no se trasladan entre
hostnames distintos. Para una dirección estable, usa el modo con dominio.

## Seguridad y diagnóstico

- Solo Nginx recibe tráfico del túnel. El conector comparte una red dedicada con
  frontend y otra para salir a Cloudflare; no pertenece a la red de la API/base.
- Nginx solo confía en `CF-Connecting-IP` procedente de `172.30.79.20`, la IP del
  conector, y conserva los límites por visitante. Las cabeceras enviadas al puerto
  local no pueden suplantar ese proxy. HTTP público se redirige a HTTPS.
- Uvicorn sigue confiando exclusivamente en la IP interna de Nginx. No se usan
  comodines de proxies, CORS ni rutas privadas. No se publican 5432 ni 8000.
- La subred dedicada es `172.30.79.0/24`. Si colisiona con otra red, hay que adaptar
  conjuntamente Compose y la IP de confianza de Nginx; no ampliar el rango confiado.
- No crees reglas de caché que incluyan `/api/`; respeta `Cache-Control: no-store`.
  No registres cookies, contraseñas ni el token del túnel. Compartir el enlace hace
  público el catálogo; la creación y administración siguen exigiendo sesión.
- Si no conecta, consulta los logs: requiere salida a Cloudflare por TCP 7844
  (se usa HTTP/2). No se necesitan puertos entrantes ni cambios en el router.
- En caso de fallo al arrancar, el script intenta detener el conector para no
  dejar una publicación incompleta. Comprueba `status` si Docker no responde.

## Pruebas antes de dar la tarea por terminada

Desde un móvil, **desactiva Wi-Fi y utiliza datos móviles**:

1. Abre el hostname HTTPS y combina los filtros.
2. Vota en elección única, múltiple y ranking. Comprueba los resultados en otro
   dispositivo sin recargar.
3. Inicia sesión en `/acceso`, crea una votación y ciérrala/reábrela. Los controles
   del otro dispositivo deben cambiar en directo.
4. En una ventana privada sin sesión, abre `/admin`: debe redirigir al acceso.
5. Ejecuta `tunnel.ps1 stop` y recarga desde datos móviles: VoteStupid debe dejar
   de responder; puede aparecer un error de Cloudflare.
6. Arranca de nuevo y comprueba que votaciones y resultados se conservan.

La prueba desde datos móviles y la configuración de la cuenta deben confirmarse
con el usuario; una prueba HTTP local no las sustituye.

### Comprobaciones realizadas el 5 de noviembre de 2026

- Quick Tunnel conectado y hall público accesible con certificado HTTPS válido.
- Seis combinaciones de filtros (estado y tipo), redirección HTTP a HTTPS y WSS.
- Voto y actualización anónimos en los tres tipos sobre votaciones de prueba,
  con eventos `results_updated` recibidos por WebSocket cifrado.
- Peticiones públicas de creación, listado administrativo y cierre sin sesión
  rechazadas; origen administrativo ajeno rechazado.
- Cabeceras locales falsas ignoradas; proxy de confianza, IP por visitante,
  rate limiting y aislamiento de la red del conector comprobados localmente.
- Al detener túnel y aplicación, el enlace dejó de servir VoteStupid (HTTP 530
  de Cloudflare). Tras arrancar otro Quick Tunnel se compararon catálogo y
  resultados públicos con la copia anterior: todos se conservaron.
- Cookie Secure y origen HTTPS exacto confirmados en el backend; 8000 y 5432 sin
  publicar. El conector temporal no recibe el token privado del túnel con nombre.

Pendiente de confirmación del usuario: datos móviles, login administrativo HTTPS,
creación, cierre y reapertura desde la interfaz y actualización entre dispositivos.
No dar la tarea completa hasta realizar esas comprobaciones. El token del túnel
con nombre permanece privado y no se necesita para el modo temporal.

Referencias: [crear un túnel con dominio](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/),
[Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
y [cabeceras de Cloudflare](https://developers.cloudflare.com/fundamentals/reference/http-headers/).
