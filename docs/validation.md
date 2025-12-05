# Escenarios de Validación (Profesor)

La cátedra verificará el proyecto pidiendo cambios pequeños y observando el pipeline. Este documento describe cómo responder.

## 1. Cambio simple en el código
**Objetivo:** demostrar que:
- Los tests unitarios corren automáticamente y generan reportes.
- El pipeline de build (GitHub Actions) se ejecuta y se visualiza el log.
- El deploy a QA refleja el cambio.
- Tras el deploy, los tests de integración pasan y se ve el informe.
- Se realiza la aprobación manual antes de pasar a producción.

**Pasos sugeridos:**
1. El profesor pide modificar, por ejemplo, el mensaje del endpoint `/`.
2. Crear una rama `hotfix/demo`, aplicar el cambio y abrir PR.
3. Verificar que `ci.yml` corra; descargar los artefactos desde la pestaña “Summary”.
4. Tras el merge, monitorear `deploy.yml`: confirmar que QA recibe la nueva versión (Cloud Run URL/`/health` mostrando nuevo mensaje).
5. Documentar el ID del deployment y adjuntarlo al informe final.

## 2. Fallo provocado en un test unitario
**Objetivo:** demostrar que el pipeline se detiene antes del deploy cuando falla una unittest.

**Pasos:**
1. Modificar temporalmente un test (por ejemplo, `test_voice_routes.py` esperando otro mensaje) o usar un flag que provoque fallo.
2. Ejecutar `ci.yml` (como PR o `workflow_dispatch`).
3. Mostrar al profesor cómo el job `backend-test` falla y cómo los jobs posteriores quedan cancelados; no hay despliegue ni integración.
4. Revertir el cambio y volver a ejecutar para dejar el repo limpio.

## 3. Falla durante pruebas de integración
**Objetivo:** evidenciar que los deploys se detienen antes de producción si un test de integración detecta un problema.

**Pasos:**
1. Tras desplegar a QA, modificar el test `integration/test_db_metadata.py` o provocar un error en la base QA (por ejemplo, revocar permisos temporalmente).
2. Ejecutar `deploy.yml` y observar que el job `integration-tests` falla, bloqueando `approval-prod`.
3. Restaurar la configuración y repetir para mostrar un pipeline exitoso.

## Evidencias a recopilar
- Capturas o links a los artefactos (reportes JUnit, coverage) de cada workflow (`ci.yml` y `deploy.yml`).
- URL de Cloud Run QA y PROD: `https://final-ing-3-api-qa-quelas-rivero-*.run.app`, `https://final-ing-3-web-qa-...`, y sus equivalentes de producción mostrando la versión esperada.
- Registro de quién aprobó manualmente el paso a producción (`environment protection history`).
- Logs de GitHub Actions que demuestran el comportamiento cuando un test falla.

Con estos escenarios documentados será más sencillo guiar al profesor paso a paso y asegurar que cada requisito de validación quede demostrado durante la defensa.
