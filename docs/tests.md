# Inventario de Tests

Resumen de los casos unitarios e integración existentes y plan para alcanzar/mostrar los ≥40 tests requeridos.

## Backend (pytest)
Actualmente hay 15 módulos unitarios bajo `backend/tests/` y 2 suites marcadas como integración.

| Archivo | Tipo | Cobertura principal |
|---------|------|--------------------|
| `test_app_endpoints.py` | Unit | `/` y `/health`, estado del servicio |
| `test_auth_endpoints.py` | Unit | Login, registro, refresh, validación de tokens |
| `test_auth_change_password.py` | Unit | Reglas de cambio seguro con throttling |
| `test_auth_password_reset_endpoints.py` | Unit | Flujo de password reset con links mágicos |
| `test_services_password_reset.py` | Unit | Utilidades de tokens, historial de contraseñas y validadores |
| `test_services_utils.py` | Unit | Helpers genéricos (hashing, validaciones, cache) |
| `test_admin_users.py` | Unit | Lógica de límites y creación de admins |
| `test_admin_users_routes.py` | Unit | Endpoints REST admin polo |
| `test_company_user_endpoints.py` | Unit | APIs para admins de empresa/usuarios finales |
| `test_tipos_routes.py` | Unit | Catálogos del tótem |
| `test_chat_routes.py` | Unit | Chatbot texto (Gemini) |
| `test_voice_routes.py` | Unit | Speech-to-Text/Text-to-Speech y validaciones |
| `test_google_auth_routes.py` | Unit | OAuth con Google |
| `test_services_utils.py` | Unit | Funciones utilitarias compartidas |
| `test_admin_users.py` | Unit | Validaciones de negocio admin |
| `test_services_password_reset.py` | Unit | Gestión de tokens y correo |
| `integration/test_google_speech.py` | Integration | Inicialización de `google-cloud-speech` con credenciales reales |
| `integration/test_db_metadata.py` | Integration | Consultas reales a PostgreSQL (metadata y conteo) |

> Nota: `rg` muestra 73 definiciones `def test_*`. Mantener o incrementar este número al refactorizar.

### Cómo ejecutar
- Unitarios: `cd backend && pytest -m "not integration" --maxfail=1 --disable-warnings`
- Integración: `cd backend && pytest -m integration --base-url=$QA_BASE_URL`

Los reportes en CI se exportarán en formato JUnit (`pytest --junitxml=report.xml`).

## Frontend (Angular)
Hay 6 specs generadas por Angular (`*.spec.ts`) que actualmente solo validan la creación del componente. El plan es:
1. Añadir pruebas de lógica (servicios, pipes) usando `TestBed` y `HttpClientTestingModule`.
2. Crear pruebas de interacción (por ejemplo, `admin-polo` interactuando con formularios) usando `ComponentFixture` + eventos.
3. Incorporar una suite E2E ligera (Playwright o Cypress) en `frontend/tests/` para validar flujos críticos: login, dashboard admin, chatbot.

### Comandos
- Unitarios Angular: `cd frontend && npm run test -- --watch=false --code-coverage`
- E2E (cuando exista): `cd frontend && npx playwright test` (o comando equivalente).

## Reportes y trazabilidad
- GitHub Actions guardará los artefactos `backend-unit-tests.xml`, `backend-integration-tests.xml`, `frontend-unit-tests.xml` y los reportes de cobertura.
- `docs/tests.md` se actualizará para listar nuevos módulos o escenarios especiales (por ejemplo, pruebas de fallos solicitadas por el profesor).
- Documentar en cada PR qué pruebas se añadieron o tocaron.

## Próximos pasos de testing
1. Reforzar specs de Angular para cubrir servicios `auth.service.ts`, `chat.service.ts` y componentes de formularios.
2. Añadir pruebas de integración HTTP que apunten al Cloud Run de QA (`/health`, `/api/voice/status`, `/auth/login`).
3. Configurar pruebas e2e en CI para ejecutarse tras el deploy QA, antes de la aprobación manual.
4. Preparar scripts/documentación para el escenario “el profesor pide cambio y falla un test”: se documentará en `docs/validation.md`.
