# Hall p?blico y administraci?n privada ? validaci?n

Fecha: 5 de noviembre de 2026. Implementaci?n y comprobaciones automatizadas
completadas. Sin commit ni push de este bloque.

## Comportamiento implementado

- HomeView mantiene la presentaci?n en `/` e incorpora el cat?logo p?blico.
  `/votaciones` muestra el listado y `/historial` redirige a ?l.
- Tarjetas con t?tulo, tipo, fecha y estado; activas y recientes primero.
  Filtros combinados, limpieza, paginaci?n, estados vac?os, errores y carga.
- Un WebSocket de cat?logo actualiza los filtros al cerrar o reabrir votaciones;
  recupera el listado tras reconectar y cancela sus esperas al salir.
- Login, logout y administraci?n privada con sesi?n de ocho horas en PostgreSQL.
  La API rechaza creaci?n y administraci?n sin sesi?n, incluso con token individual.
- Recuperaci?n de votaciones anteriores mediante la sesi?n global. No se guardan
  nuevos tokens administrativos en almacenamiento local ni en enlaces.
- Cookie HttpOnly, SameSite Strict y Secure por defecto; hash scrypt, control de
  origen y cabecera, l?mites de intentos y revocaci?n/caducidad.
- Retirados la vista y el servicio del hist?rico local que ya no ten?an ruta.
- Corregidos respuestas tard?as, duplicados de paginaci?n y mensajes heredados.
- La retirada del token antiguo de la URL conserva el estado de Vue Router;
  se a?adi? una regresi?n para evitar el aviso y problemas de navegaci?n.
- Cierre por fecha coherente en API y vistas. Reabrir expl?citamente una votaci?n
  con plazo vencido retira ese plazo para permitir votar de nuevo.

## Pruebas automatizadas

- Backend: **195 tests superados**, ejecutados con `pytest -v`.
- Frontend: **38 tests superados**; `npm run build` correcto.
- Casos de autorizaci?n real independientes de las sustituciones usadas en
  regresiones antiguas: visitantes, cookies, CSRF, sesi?n caducada, logout,
  rotaci?n, recuperaci?n de acceso, rate limiting, filtros y eventos WebSocket.
- Pruebas de vistas: filtros, errores/vac?os, paginaci?n, respuestas tard?as,
  desmontaje, reconexi?n, enlaces sin secretos y cierre programado.

## Comprobaciones en navegador

- Portada p?blica en escritorio y m?vil de 375 px.
- Login y listado administrativo en m?vil; redirecci?n del acceso directo sin sesi?n.
- Recuperaci?n de la votaci?n de prueba anterior sin conservar su token.
- Cierre/reapertura y confirmaciones desde el panel m?vil.
- Panel y formulario de creaci?n en 375 y 768 px; listado privado en tablet.
- Logout real con regreso al acceso privado.
- Filtros combinados y limpieza comprobados en la sesi?n anterior.
- Cat?logo m?vil filtrado por inactivas: reapertura desde otro cliente cambia
  el total de 8 a 7 sin recargar. Nuevo cierre lo devuelve a 8.
- Interrupci?n real del backend: aviso visible; al arrancarlo, reconexi?n
  autom?tica, desaparici?n del aviso y recuperaci?n del cat?logo sin recargar.

Estas comprobaciones no equivalen a repetir una matriz exhaustiva de todas las
vistas, tama?os y recorridos ?nicamente con teclado. Tampoco se ha repetido hoy
el voto de los tres tipos desde navegador; esos flujos est?n cubiertos por las
pruebas automatizadas y las validaciones anteriores del proyecto.

## Configuraci?n y persistencia

La migraci?n `a721c409dd10` ya se aplic? en desarrollo durante la sesi?n anterior,
conservando las votaciones existentes. PostgreSQL conserva votaciones, votos y
sesiones; el cat?logo actual muestra los datos de la sesi?n anterior.

El usuario debe elegir su contrase?a definitiva localmente:

```powershell
python scripts/configure_admin.py --write-env --local-http
```

No hay contrase?a predeterminada. Para producci?n omitir `--local-http` y usar
HTTPS. Reiniciar el backend tras configurar la contrase?a. Las pruebas de navegador
usaron una credencial temporal solo en el proceso; no se guard? en el `.env`.
Frontend y API deben usar el mismo hostname, por ejemplo `localhost`.

## Entrega

Consultar README y la gu?a de seguridad actualizados. Revisar `git diff` antes
del commit. AGENTS.md, los tres archivos locales y los archivos privados de entorno
siguen excluidos de Git. No eliminar el volumen de PostgreSQL al detener servicios.
