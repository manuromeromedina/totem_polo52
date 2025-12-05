# Setup & Configuración de Entornos

Guía para desarrollar localmente y preparar los ambientes QA/PRO sobre Google Cloud Run (backend + frontend).

## Dependencias locales
- Python 3.11+ y `pip`
- Node.js 20 + npm 10
- PostgreSQL 14 o superior
- Google Cloud CLI (`gcloud`) para probar despliegues manuales
- Docker/Docker Compose (requerido a partir del siguiente paso del plan)

## Variables de entorno
Crea un archivo `.env` en la raíz copiando `.env.example` y ajustando valores reales.

Campos obligatorios para desarrollo:
- `DATABASE_URL`: cadena de conexión PostgreSQL para FastAPI (usa `postgresql+psycopg2://user:pass@host:5432/db`).
- `SECRET_KEY` y `SESSION_SECRET_KEY`: claves para JWT y sesiones.
- `EMAIL_USER`, `EMAIL_PASS`, `SMTP_SERVER`, `SMTP_PORT`: credenciales SMTP (se recomienda Gmail con app password).
- `GOOGLE_API_KEY`, `GEMINI_MODEL`, `GOOGLE_APPLICATION_CREDENTIALS`: necesarios para chatbot + voz.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`: OAuth2 de Google.
- `API_URL`: URL del backend consumida por Angular (se usa mediante reemplazo antes del build).

Variables pensadas para CI/CD:
- `QA_DATABASE_URL` / `PROD_DATABASE_URL`: conexiones específicas usadas en los despliegues.
- `QA_BASE_URL` / `PROD_BASE_URL`: URL pública tras el deploy (Cloud Run) para las pruebas de integración.
- `GCP_PROJECT_ID`, `GCP_REGION`: datos del proyecto en Google Cloud.

## GitHub Actions Secrets
En `Settings > Secrets and variables > Actions` crear los siguientes secretos:
- `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SA_KEY` (JSON completo de la service account con permisos Artifact Registry + Cloud Run).
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: el mismo JSON pero pensado para escribirse como archivo temporal para los tests.
- `DATABASE_URL_QA`, `DATABASE_URL_PROD`.
- `EMAIL_USER`, `EMAIL_PASS`, `SECRET_KEY`, `SESSION_SECRET_KEY` (o agrupar en `BACKEND_ENV` si se decide inyectar como archivo).
- `API_URL_QA`, `API_URL_PROD` (para reemplazar `environment.ts` antes del build del frontend).

## Google Cloud Run
1. Crear proyecto o usar uno existente (`gcloud projects create <id>`).
2. Habilitar APIs: `gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com`.
3. Crear repositorio Artifact Registry (tipo docker) `totem` en la región elegida.
4. Crear service account `github-actions-totem` con roles `roles/run.admin`, `roles/artifactregistry.admin`, `roles/iam.serviceAccountUser`.
5. Descargar la clave JSON y guardarla en el secreto `GCP_SA_KEY`.
6. Provisionar servicios Cloud Run vacíos para reservar URLs:
   ```bash
   gcloud run deploy totem-api-qa --image gcr.io/cloudrun/hello --region $GCP_REGION --allow-unauthenticated
   gcloud run deploy totem-api-prod --image gcr.io/cloudrun/hello --region $GCP_REGION --allow-unauthenticated
   ```
7. Repetir el paso anterior para el frontend, creando servicios `totem-web-qa` y `totem-web-prod`. Estas imágenes se basarán en NGINX y servirán la carpeta `dist/frontend/browser`.
8. Configurar variables de entorno en cada servicio (`DATABASE_URL`, `SECRET_KEY`, etc. para backend; `API_URL` si se requiere en frontend) o usar Secret Manager y referencias en el deploy.

## Manejo de secretos en los pipelines
- El workflow generará un archivo `gcp-creds.json` temporal usando `GOOGLE_APPLICATION_CREDENTIALS_JSON` para ejecutar tests de voz/integración.
- `DATABASE_URL_*` se inyectarán como variables de entorno durante `pytest` y en el deploy de Cloud Run.
- Angular recibirá `API_URL` mediante `export API_URL=... && npm run build` para que el `environment.ts` se sobrescriba dinámicamente (script a definir en el siguiente paso).

Con esta configuración cualquier desarrollador puede levantar la app localmente y los pipelines tendrán toda la información necesaria para construir y desplegar ambos servicios en Google Cloud Run.
