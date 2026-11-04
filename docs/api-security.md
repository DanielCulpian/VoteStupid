# Seguridad y despliegue de la API

## Límites de entrada

La API admite títulos de 1–255 caracteres, descripciones de hasta 5.000,
entre 2 y 50 opciones de 1–255 caracteres y hasta 50 identificadores por voto.
Recorta los espacios exteriores y rechaza campos adicionales, opciones vacías,
UUID inválidos y fechas sin zona horaria. Los casos de uso siguen comprobando
pertenencia de opciones, duplicados, tipo de voto y cierre de la votación.
El cuerpo HTTP completo está limitado a **64 KiB**, también sin `Content-Length`.
Los valores excesivos devuelven `422`; un cuerpo excesivo devuelve `413`.

## Protección frente a abusos

Los límites usan una ventana móvil de 60 segundos por IP, compartida entre
votaciones e independiente del token. Los intentos inválidos también cuentan.

| Operación | Peticiones por minuto e IP |
| --- | ---: |
| Creación de votaciones | 10 |
| Registro y modificación de votos, conjuntamente | 30 |
| Todas las operaciones administrativas, conjuntamente | 30 |
| Aperturas WebSocket | 30 |
| Total HTTP y WebSocket | 300 |

Una petición excesiva recibe `429` y `Retry-After` en segundos. Las lecturas públicas
mantienen su cupo cuando se agota el administrativo. Hay un máximo de 20 sockets
simultáneos por IP y 1.000 por proceso. La denegación WebSocket usa HTTP 429 si el
servidor admite esa extensión; en caso contrario rechaza el handshake con 1008.
El canal solo publica resultados y estado; los mensajes del cliente cierran el canal.

No se guardan IP en PostgreSQL ni se exigen cuentas. Los contadores son temporales,
acotados a 10.000 claves y se reinician con el proceso. Si se llena ese registro,
se rechazan claves nuevas temporalmente, sin expulsar las que protegen un cupo.
Las personas que comparten IP también comparten límites.

Este mecanismo está pensado para **un único worker**. Con varios procesos cada
uno tendría su cupo y su registro WebSocket. Antes de escalar, centralizar ambos
registros o aplicar límites coordinados en Nginx; no se ha añadido Redis ni un
servicio externo. Estos límites no sustituyen la protección volumétrica del proxy.

## Tokens, errores y caché

El token administrativo original solo se devuelve en la creación y se utiliza
mediante `X-Admin-Token`; el del participante usa `X-Voter-Token`. Se almacenan
hashes y la comparación administrativa sigue siendo de tiempo constante.
Los errores `422` no incluyen los valores recibidos ni contexto de validadores;
los `500` muestran un mensaje genérico y su log omite la excepción y sus datos.
Los logs estándar de acceso de Uvicorn omiten la query completa. No activar logs
de cuerpos, cabeceras de autenticación o parámetros SQL en producción.

Las respuestas llevan `Cache-Control: no-store`. Configurar además Cloudflare y
Nginx para no cachear `/api/`; las reglas de caché del proxy no deben anularlo.
No registrar `X-Admin-Token`, `X-Voter-Token`, cuerpos ni `$request_uri` con query.
El enlace privado del frontend lleva el secreto en el fragmento `#token=`, que
el navegador no envía al servidor. No usar `?token=` ni ponerlo en rutas.

## CORS y proxies de confianza

`CORS_ALLOWED_ORIGINS` contiene orígenes exactos separados por comas. Por defecto
solo permite `http://localhost:5173`. Para usar también el puerto de desarrollo
5174 hay que declararlo explícitamente. En producción usar exclusivamente el
dominio HTTPS del frontend, sin `/` final, rutas ni comodines. El mismo listado
se aplica al `Origin` del handshake WebSocket. Los clientes sin `Origin`, como
herramientas HTTP, siguen sujetos a tokens y límites; CORS no es autenticación.

La aplicación usa `scope.client`, establecido por Uvicorn, e ignora directamente
`X-Forwarded-For` y `CF-Connecting-IP`. Arrancar detrás de Nginx con un único worker:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips="127.0.0.1" --ws-max-size 1024
```

No usar `--forwarded-allow-ips="*"`. Si Nginx se ejecuta en otra dirección o red,
declarar solo sus direcciones reales y restringir el acceso directo al backend.

En el futuro recorrido **Cloudflare → cloudflared → Nginx → Uvicorn**, Nginx debe
aceptar tráfico únicamente desde el túnel y validar la IP que Cloudflare aporta.
En un listener local dedicado al túnel, la base de configuración sería:

```nginx
listen 127.0.0.1:8080;
set_real_ip_from 127.0.0.1;
real_ip_header CF-Connecting-IP;

location /api/ {
    client_max_body_size 64k;
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_read_timeout 3600s;
    proxy_cache off;
}
```

`$connection_upgrade` requiere el `map` habitual de WebSocket en el bloque `http`:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

Este fragmento es una guía, no un despliegue aplicado: verificar la topología,
la IP efectiva de cloudflared y las reglas de acceso antes de publicarlo. Sobrescribir
la IP reenviada evita confiar en cadenas `X-Forwarded-For` enviadas por el cliente.
Configurar timeouts y límites de conexiones adicionales en el proxy al desplegar.

Referencias: [proxies de confianza en FastAPI](https://fastapi.tiangolo.com/advanced/behind-a-proxy/),
[módulo real IP de Nginx](https://nginx.org/en/docs/http/ngx_http_realip_module.html)
y [cabeceras de Cloudflare](https://developers.cloudflare.com/fundamentals/reference/http-headers/).
