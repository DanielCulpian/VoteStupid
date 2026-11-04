# Hall público y administración privada — punto de continuación

Estado: **implementación parcial, pendiente de validación integral**. No se ha
hecho commit ni push. La base de datos de desarrollo y su `.env` no se han modificado.

## Implementado y comprobado automáticamente

- `/` conserva `HomeView` como presentación e incorpora un catálogo público.
- `/votaciones` presenta el listado; `/historial` redirige a él.
- Tarjetas responsive con metadatos, filtros combinados, paginación, carga, error,
  vacío, limpieza de filtros y una suscripción WebSocket de catálogo.
- Endpoints de listado con proyección explícita de campos públicos y orden por
  disponibilidad y fecha. Consideran también el cierre programado.
- `/acceso`, `/admin` y `/admin/crear`; protección de rutas y redirección al caducar.
- Creación y operaciones administrativas exigen sesión también en peticiones API.
  Los tokens individuales siguen validándose si se proporcionan, pero no sustituyen
  la sesión; el administrador puede recuperar cualquier votación sin su token.
- Contraseña scrypt por entorno; cookie HttpOnly, SameSite Strict y Secure por
  defecto; sesiones de ocho horas con hash en PostgreSQL, revocación y cambio de
  contraseña; protección de origen/cabecera y límites de intentos de acceso.
- Migración `a721c409dd10` y generador interactivo `scripts/configure_admin.py`.
- Última comprobación: **192 tests backend**, **35 tests frontend** y build correcto.

Las regresiones antiguas usan un administrador autorizado de prueba. Los tests
de `test_admin_session_and_catalog.py` ejercitan una instancia real sin sustituir
la autorización: visitantes, cookies, permisos, logout, caducidad, rotación, intentos
repetidos, filtros y eventos de catálogo.

## Pendiente antes de dar la tarea por terminada

1. Revisar el diseño en navegador, móvil, tablet y escritorio. No se ha validado
   visualmente este nuevo diseño ni completado su navegación con teclado.
2. Configurar una contraseña elegida por el usuario. Ejecutar el generador y añadir
   su salida `ADMIN_PASSWORD_HASH=...` al `.env` privado. No existe contraseña por
   defecto. Documentar estas variables en `.env.example` y en la guía de seguridad.
3. Aplicar y comprobar `alembic upgrade head` en desarrollo y verificar la migración
   sobre datos existentes. Hasta entonces no está creada la tabla de sesiones en
   la base de desarrollo; las pruebas crean su tabla exclusivamente en la base test.
4. Para HTTP local, configurar explícitamente `ADMIN_COOKIE_SECURE=false`. En
   producción debe ser `true`, con HTTPS. Comprobar que frontend y API usan el
   mismo hostname (por ejemplo, ambos `localhost`) para SameSite Strict. Validar el
   flujo real de login, persistencia de cookie, logout, caducidad y reanudación.
5. Ampliar las pruebas de UI del catálogo, guardas y navegación. Las pruebas de
   servicios cubren las consultas combinadas, pero falta ejercitar los filtros
   montados, limpiar/vacíos, paginación y cambios en directo con dos navegadores.
6. Revisar y retirar o migrar `LegacyHistoryView.vue`, actualmente sin ruta pública
   y conservada temporalmente para las regresiones del antiguo histórico local.
   No debe utilizarse como interfaz de administración del sistema nuevo.
7. Revisar los mensajes de login/caducidad y los textos heredados de enlaces secretos;
   completar copia de enlaces públicos y navegación privada donde sea necesario.
8. Verificar cierre/reapertura, fechas de cierre cumplidas, reconexión y estado de
   filtros con datos reales; revisar las respuestas tardías y los temporizadores.
9. Actualizar README/guía de seguridad, revisar el diff completo y ejecutar de nuevo
   toda la suite y build después de las correcciones. Preparar el commit final.

## Servicios al cerrar este bloque

Se ha solicitado detener FastAPI, Vite y el contenedor `votestupid-db`, conservando
el volumen de PostgreSQL. No se han detenido servicios ajenos al proyecto.

Para continuar: leer este informe, revisar `git status`, arrancar PostgreSQL,
configurar las variables privadas, aplicar la migración y arrancar backend/frontend.
No publicar ni desplegar este punto intermedio como una tarea terminada.
