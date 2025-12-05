# Pipelines (GitHub Actions)

Este documento describe los workflows que se implementarán para cumplir con los requisitos de build, tests, despliegue en QA, pruebas de integración y aprobación manual previa a producción usando únicamente Google Cloud Run y GitHub Actions.

## Workflow `ci.yml`
**Disparadores**: `pull_request` hacia `main` y `push` a cualquier rama.

**Jobs**
1. `frontend-test`
   - Configura Node 20, restaura cache (`npm` + `~/.npm`).
   - Ejecuta `npm ci`, `npm run lint` (opcional) y `npm run test -- --watch=false --code-coverage`.
   - Publica artefactos `frontend-unit-tests.xml` y carpeta `coverage/`.
2. `backend-test`
   - Configura Python 3.11, instala dependencias (`pip install -r requirements.txt`).
   - Ejecuta `pytest -m "not integration" --junitxml=backend-unit-tests.xml`.
   - Sube reportes como artefacto.

**Resultado**: bloqueo obligatorio para merge; los reportes estarán disponibles para descargar.

## Workflow `deploy.yml`
**Disparadores**: `push` a `main` o `workflow_dispatch`.

**Jobs**
1. `call-ci`
   - Usa `workflow_call` para reutilizar el testing de `ci.yml`. Si falla, el pipeline termina.
2. `build-backend`
   - Construye la imagen Docker (`backend/Dockerfile`), etiqueta `us-central1-docker.pkg.dev/final-ing-3/final-ing-3-repo/backend:$GITHUB_SHA`.
   - Push a Artifact Registry usando `gcloud auth configure-docker` + secreto `GCP_SA_KEY`.
   - Publica `image-digest` como output.
3. `build-frontend`
   - Instala Node, ejecuta `npm ci && API_URL=$QA_API_URL npm run build`.
   - Construye la imagen NGINX (`frontend/Dockerfile`) que sirve `dist/frontend/browser`.
   - Push al mismo Artifact Registry (`final-ing-3-repo/frontend`).
4. `deploy-backend-qa`
   - Usa `google-github-actions/deploy-cloudrun@v2`.
   - Variables: `service: final-ing-3-api-qa-quelas-rivero`, `region: us-central1`, `image: <digest>`.
   - Inyecta `.env` QA mediante secretos `DATABASE_URL_QA`, `SECRET_KEY`, etc.
5. `deploy-frontend-qa`
   - Usa `google-github-actions/deploy-cloudrun@v2` con `service: final-ing-3-web-qa-quelas-rivero` y la imagen subida en el job previo.
6. `integration-tests`
   - Corre `pytest -m integration --base-url=$QA_BASE_URL` (y Playwright si aplica) apuntando al entorno recién desplegado.
   - Publica reportes y marca `QA_URL` como evidencia.
7. `approval-prod`
   - Job vacío con `environment: production` y `needs: integration-tests`. Requiere aprobación manual desde la UI de GitHub Actions.
8. `deploy-backend-prod`
   - Igual que QA pero con servicio `final-ing-3-api-prod-quelas-rivero` y secretos de producción.
9. `deploy-frontend-prod`
   - Repite el proceso Cloud Run con `service: final-ing-3-web-prod-quelas-rivero` y `API_URL=$PROD_API_URL`.

## Workflow `manual-validation.yml`
Opcionalmente se añadirá un workflow disparado con `workflow_dispatch` para simular los escenarios del profesor:
1. Job `break-unit-test`: modifica un archivo o ejecuta un script que falla un test; confirma que el pipeline se detenga antes de deploy.
2. Job `small-code-change`: aplica un parche mínimo (p.ej., cambiar un string) y ejecuta `ci.yml` completo para mostrar reportes.

## Artefactos y notificaciones
- Todos los workflows publicarán archivos `.xml` y `coverage/` para revisión.
- Se puede integrar Slack/Teams enviando notificación en `approval-prod` y `deploy-*` con `actions/checkout` + `slackapi/slack-github-action` (pendiente a confirmar con la cátedra).

## Estrategia de rollback
- Cloud Run mantiene revisiones anteriores, por lo que se puede usar `gcloud run services update-traffic final-ing-3-api-prod-quelas-rivero --to-latest=false --revision <id>` si algo falla.
- Cloud Run conserva revisiones previas, permitiendo reasignar tráfico a cualquier revisión anterior.

Con estos workflows se cubre el requisito: cada PR corre tests y muestra reportes; el merge a `main` construye y despliega automáticamente a QA, ejecuta pruebas de integración y requiere aprobación manual antes de promover a producción.
