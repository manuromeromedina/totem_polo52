# Backend — Polo 52

API del Parque Industrial Polo 52: gestión de empresas/usuarios/contactos/servicios/lotes y el asistente conversacional (chat + voz) del tótem.

## Stack técnico

- **Framework**: FastAPI (`app/main.py`)
- **Lenguaje y versión**: Python 3.11 (`backend/Dockerfile`: `python:3.11-slim`)
- **Servidor ASGI**: Uvicorn
- **Base de datos**: PostgreSQL (vía Supabase en el entorno actual — `DATABASE_URL` con driver `psycopg2-binary`)
- **ORM**: SQLAlchemy (modelos declarativos en `app/models.py`, `Base`/`engine`/`SessionLocal` en `app/config.py`). Sin Alembic ni otra herramienta de migraciones: las tablas se crean con `Base.metadata.create_all()` al arrancar (`app/bootstrap.py`)
- **Validación de datos**: Pydantic (`app/schemas.py`), con `email-validator` para los campos de tipo `EmailStr`
- **Autenticación**:
  - JWT propio (`python-jose`, algoritmo `HS256`, `SECRET_KEY`) para login con usuario/contraseña (`app/routes/auth.py`), con hashing de contraseñas vía `passlib`
  - Control de acceso por rol (`admin_polo`, `admin_empresa`, `publico`) mediante dependencias de FastAPI (`require_admin_polo`, `require_empresa_role`, `require_public_role`) sobre las tablas `usuario`/`rol`/`rol_usuario`
  - Login con Google vía OAuth2/OIDC (`Authlib`, `app/routes/google_auth.py`), con `itsdangerous`/`SessionMiddleware` para el estado de sesión del flujo OAuth
- **IA / NLP (asistente conversacional)**: Google Gemini vía `google-generativeai` (`app/services/chatbot_service.py`). Pipeline propio de texto → SQL de solo lectura sobre una whitelist de tablas, con selección resiliente de modelo (`GEMINI_MODEL`, con fallback a otros modelos de la familia Gemini si el configurado no está disponible). Sin frameworks externos tipo Dialogflow/Rasa
  - **Voz**: Google Cloud Speech-to-Text y Google Cloud Text-to-Speech (`google-cloud-speech`, `google-cloud-texttospeech`, `app/services/voice_service.py`), autenticado con una service account (`GOOGLE_APPLICATION_CREDENTIALS`)
- **Testing**: pytest (+ `pytest-asyncio`, `pytest-mock`, `pytest-cov`/`coverage`, `Faker` para datos de prueba), usando `fastapi.testclient.TestClient`. Suite en `backend/tests/` (unitarios, de rutas/integración y `tests/integration/`). Configuración en `pytest.ini`.
  - Nota: estas libs de testing están instaladas en el entorno pero no están pineadas en `requirements.txt` (no hay un `requirements-dev.txt` separado en el repo)
- **Otras dependencias clave** (`requirements.txt`):
  - `httpx` — cliente HTTP (usado también por `TestClient`)
  - `python-multipart` — parseo de `multipart/form-data` (login con `OAuth2PasswordRequestForm`)
  - `python-dotenv` — carga de variables de entorno desde `.env`
  - `typing_extensions` — tipado (`TypedDict`, etc.)
- **Rate limiting**: implementación propia en memoria por IP (`app/rate_limit.py`), sin Redis ni librería externa — pensada para un único proceso/worker
- **Email transaccional**: SMTP directo (`smtplib`, ver `app/services/email_service.py`), configurado por `SMTP_SERVER`/`SMTP_PORT`/`EMAIL_USER`/`EMAIL_PASS`
- **Contenedores / despliegue**: Docker (`Dockerfile`), imagen publicada a GitHub Container Registry en cada push a `main` vía `.github/workflows/docker-ghcr.yml`. Ver `DOCKER.md` para el detalle de build/run/publish.

## Cómo correr el proyecto

### Requisitos
- Python 3.11
- Una base PostgreSQL accesible (local o remota)

### Setup

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Variables de entorno

Crear `backend/.env` (no se commitea, ver `.gitignore`) con las variables que use el código:

```dotenv
# Obligatorias
DATABASE_URL=postgresql://usuario:password@host:5432/nombre_db
SECRET_KEY=una_clave_secreta_para_firmar_jwt
SESSION_SECRET_KEY=otra_clave_para_sessionmiddleware

# IA / voz (asistente conversacional)
GOOGLE_API_KEY=tu_api_key_de_gemini
GEMINI_MODEL=gemini-flash-lite-latest       # opcional, tiene default
GOOGLE_APPLICATION_CREDENTIALS=/ruta/al/service-account.json  # opcional, solo si se usa voz

# Google OAuth (login con Google)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Email (recuperación de contraseña, notificaciones)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=...
EMAIL_PASS=...

# URLs / CORS
FRONTEND_BASE_URL=http://localhost:4200
EXTERNAL_BASE_URL=http://localhost:8000
CORS_ALLOW_ORIGINS=http://localhost:4200
ROOT_PATH=

# Bootstrap del admin inicial (solo hace falta la primera vez, si no hay ningún admin_polo)
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=una_password_segura
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_CUIL=20000000000
POLO_CUIL=20000000000
```

### Levantar el servidor

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Docs interactivas (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

Al arrancar, `app/bootstrap.py` crea las tablas si no existen, siembra los catálogos de referencia (`tipo_vehiculo`, `tipo_contacto`, `tipo_servicio_polo`, `tipo_servicio`) y crea el usuario `admin_polo` inicial si no hay ninguno (usando `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD`).

### Correr los tests

```bash
cd backend
pip install pytest pytest-asyncio pytest-mock pytest-cov faker  # si no están instalados
pytest
```

### Docker

Ver [`DOCKER.md`](./DOCKER.md) para build/run local y publicación a GHCR.
