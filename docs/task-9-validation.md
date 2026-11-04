# Tarea 9 — Verificación integral

Fecha: 4 de noviembre de 2026. Entorno: Windows, PostgreSQL en Docker,
FastAPI con un worker y Vue servido por Vite.

## Resultado

- Backend: **188 tests superados**, incluidos 10 nuevos.
- Frontend: **32 tests superados**.
- Total: **220 tests superados**.
- `npm run build`: correcto.

## Cobertura añadida

Los nuevos tests verifican resultados, puntos y porcentajes exactos para los tres
tipos de votación; entrega del mismo evento a dos suscriptores; aislamiento entre
votaciones; ausencia de eventos por votos rechazados; cierre, reapertura y nueva
suscripción; varios votantes concurrentes; envíos duplicados simultáneos y limpieza
de suscriptores WebSocket fallidos. La suite conserva las comprobaciones de
administración, histórico, validación, rate limiting y privacidad existentes.

## Problema encontrado y corregido

Dos peticiones simultáneas con el mismo token podían superar ambas la consulta
inicial de duplicados. PostgreSQL conservaba un único voto, pero la petición que
perdía la carrera devolvía HTTP 500. El repositorio transforma ahora exclusivamente
la violación de `uq_vote_poll_voter` en un rechazo de voto: **201 + 409**, con un solo
voto guardado. Los demás errores de integridad siguen propagándose como errores
internos. La prueba reproduce la carrera mediante una barrera y sesiones SQL
independientes, sin depender de esperas arbitrarias.

## Comprobaciones reales en navegador

Se crearon votaciones única, múltiple y ranking desde el formulario y se registraron
dos participantes por votación usando los perfiles normal y privado de Vivaldi.
Se modificaron los tres tipos de voto, se reordenó el ranking y se verificaron los
resultados en directo, el histórico y su acceso al panel administrativo. El cierre
bloqueó al otro participante y la reapertura recuperó sus controles sin recargar.

Se detuvo FastAPI, se reinició realmente PostgreSQL conservando su volumen y se
arrancó otra vez la aplicación. Los clientes mostraron el aviso y reconectaron
automáticamente. Los datos públicos y resultados completos de las tres votaciones
coincidieron exactamente con los capturados antes del reinicio, incluida una
votación cerrada. El histórico y el acceso administrativo siguieron disponibles.

No quedan errores críticos conocidos en los flujos comprobados. Esta validación
local no sustituye las pruebas del futuro despliegue con Nginx y Cloudflare Tunnel.

## Repetir las pruebas automatizadas

Desde la raíz, con PostgreSQL y `votestupid_test` disponibles:

```powershell
$env:PYTHONPATH = 'backend'
.\.venv\Scripts\python.exe -m pytest -v
```

Desde `frontend/`:

```powershell
npm test
npm run build
```
