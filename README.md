# Totem Polo52

Aplicación integral (Angular + FastAPI + PostgreSQL) para operar el tótem interactivo del Parque Industrial Polo 52. El sistema ofrece login JWT y Google OAuth, paneles separados para administradores del polo y de empresas, chatbot con voz (Gemini + Google Speech) y workflows de recuperación/rotación de contraseñas.

## Arquitectura
- **Frontend**: Angular 19, componentes standalone, interceptores para adjuntar tokens, servicios especializados para panel público, admin polo, admin empresa, chat y flujos de password reset.
- **Backend**: FastAPI, SQLAlchemy ORM y modelos normalizados (empresa, usuario, roles, servicios). Los módulos `routes/`, `schemas/` y `services.py` encapsulan login JWT, recuperación por email, cache de tokens usados y chatbot de voz.
- **Base de datos**: PostgreSQL. SQLAlchemy gestiona relaciones, cascadas y sesiones (`SessionLocal`).
- **Testing**: Pytest con 15 módulos unitarios (≈70 tests) y 2 suites de integración (`backend/tests/integration`). El frontend conserva 6 specs de Angular (pieza a reforzar).

## Estructura del repositorio
```
backend/
  app/        # Código FastAPI
  tests/      # Unit & integration tests (pytest)
  docs/       # Historias de usuario y reportes actuales
frontend/
  src/        # Angular 19 standalone app
  tests/      # (Futuros e2e)
docs/         # Documentación operativa del proyecto (se llena en este plan)
pytest.ini    # Configuración global de pytest
```

## Cumplimiento de requisitos del integrador
| Requisito | Estado actual | Próximos pasos |
|-----------|---------------|----------------|
| App completa en GitHub con frontend, backend y BD | ✅ Repositorio FastAPI + Angular funcionando con PostgreSQL | Documentar cómo levantarlo localmente y preparar ambiente QA |
| ≥40 tests unitarios + integración | ✅ 73 unit tests backend, 2 de integración (GCloud Speech + metadata DB). Frontend con specs básicos | Añadir specs significativos al frontend y detallar reportes |
| Build & deploy automatizados (Google Cloud Run + GitHub Actions) | ✅ `deploy.yml` publica imágenes y despliega en Cloud Run QA/PROD | Mantener secretos y repositorio Artifact Registry `final-ing-3-repo` |
| Ejecución de tests y reportes en cada PR | ✅ `ci.yml` corre Angular + Pytest y publica artefactos | Revisar cobertura y reportes en cada PR |
| Deploy automático a QA + pruebas de integración | ✅ Workflow despliega backend/web en QA y corre `pytest -m integration` | Actualizar `QA_API_URL` al cambiar la URL de Cloud Run |
| Aprobación manual antes de producción | ✅ Job `approval-prod` bloquea el deploy final hasta que un reviewer autorice | Configurar environment `production` con reviewers |
| Documentar Test Cases unitarios e integración | ⚠️ Parcial (solo `backend/docs/test-report.md`) | Completar `docs/tests.md` |

## Variables de entorno
Todos los servicios leen variables desde `.env`. Use `.env.example` (crear en este plan) para replicar localmente y rellenar secretos en GitHub Actions.

Backend principales:
- `DATABASE_URL` (`postgresql+psycopg2://user:pass@host:5432/db`)
- `SECRET_KEY`, `SESSION_SECRET_KEY`, `ENVIRONMENT`
- `EMAIL_USER`, `EMAIL_PASS`, `SMTP_SERVER`, `SMTP_PORT`
- `GOOGLE_API_KEY`, `GEMINI_MODEL`, `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`

Frontend:
- `environment.ts` define `apiUrl`. En CI/CD se sobreescribirá con `API_URL` antes de compilar.

## Levantar localmente
1. Clonar el repo y crear `.env` a partir de `.env.example`.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   npm run start
   ```
4. Navegar a `http://localhost:4200` (frontend) y API en `http://localhost:8000/docs`.

### Con Docker / Docker Compose
- Construir imágenes individuales:
  ```bash
  make build-backend
  make build-frontend
  ```
- Levantar entorno local con PostgreSQL usando Docker Compose:
  ```bash
  make compose-up
  # o directamente
  docker compose -f docker-compose.dev.yml up --build
  ```
  Esto levanta `db` (Postgres) y `api` (FastAPI con Uvicorn). Recuerda actualizar `DATABASE_URL` si cambias credenciales.

## Estrategia de testing
- **Backend unit**: `pytest -m "not integration"` (por defecto en CI). Incluye rutas de auth, admin, chat, servicios de voz, utilidades y validaciones.
- **Backend integración**: `pytest -m integration` apunta a Google Cloud Speech y consultas reales a PostgreSQL. En CI se ejecutarán luego del deploy a QA usando `BASE_URL` expuesta como secret.
- **Frontend**: Angular `ng test --code-coverage` (ya configurado). Se agregarán specs adicionales y posibles pruebas e2e (Playwright/Cypress) dentro del directorio `frontend/tests/`.

## Roadmap CI/CD
1. **Dockerización**: crear Dockerfiles independientes. El backend se empacará como imagen Python (Uvicorn). El frontend se buildará y servirá con NGINX dentro de un contenedor estático.
2. **GitHub Actions**:
   - `ci.yml`: en PR y push. Jobs de Node/Python con caches, reportes JUnit/coverage como artefactos.
   - `deploy.yml`: tras merge en `main`, reutiliza tests, construye imágenes, sube a Artifact Registry y despliega QA (dos servicios Cloud Run: backend y frontend). Luego corre `pytest -m integration` contra QA.
   - `production.yml` o job final con `environment: production` y aprobación manual para promover builds a PRO.
3. **Cloud**:
   - Backend: Google Cloud Run (`totem-api-qa` y `totem-api-prod`) usando Artifact Registry gcr repo `totem`.
   - Frontend: Google Cloud Run (`totem-web-qa` y `totem-web-prod`) usando la imagen NGINX generada.

## Documentación adicional
El directorio `docs/` contendrá:
1. `setup.md`: variables, dependencias, cómo cargar secretos (GitHub + GCP).
2. `tests.md`: inventario de casos unitarios/integración y cómo interpretarlos.
3. `pipelines.md`: detalle de los workflows, ambientes y manual approval.
4. `validation.md`: guías para los escenarios de validación que pedirá el profesor (cambios en código/test y cómo afectan el pipeline).

Con esto el proyecto queda listo para los siguientes pasos: contenerizar, automatizar pipelines y preparar despliegues QA/Prod enteramente sobre Google Cloud Run.
