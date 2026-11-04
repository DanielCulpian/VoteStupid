# VoteStupid
Anonymous voting platform for friends

## Histórico de votaciones

Abre **Histórico** desde el inicio, la creación o la administración. Las votaciones
creadas desde la aplicación se recuerdan en ese perfil del navegador, con título,
tipo, fecha y último estado conocido. La vista consulta los identificadores
guardados para actualizar sus datos; no existe un listado global público.

Las votaciones, los votos y sus resultados se guardan en PostgreSQL. La lista del
histórico se guarda en `localStorage`, sin tokens, hashes ni enlaces privados.
Cualquier persona que utilice el mismo perfil del navegador puede ver esa lista.

El acceso de administración se conserva únicamente en `sessionStorage` y el
backend vuelve a validar el token al utilizarlo. Guarda siempre el enlace privado
que recibes al crear una votación. Si cambias de navegador, borras sus datos o
pierdes la sesión, usa **Recuperar una votación anterior** con ese enlace completo.
Un enlace público permite consultar resultados, pero no recuperar la administración.

El volumen `postgres_data` de `compose.yaml` conserva la base de datos al detener
y arrancar el contenedor. Puedes comprobarlo con `docker compose restart db` y
volver a abrir el histórico cuando PostgreSQL y FastAPI estén disponibles.

## Comprobaciones

Desde la raíz, con el entorno virtual activado, configura `PYTHONPATH=backend` y
ejecuta `python -m pytest -v`. Las pruebas de integración usan `votestupid_test`.
Desde `frontend/`, ejecuta `npm test` y `npm run build` para comprobar la lógica y
compilar la aplicación.
