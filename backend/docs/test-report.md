# Informe de Pruebas – Backend Polo52

Esta documentación resume todas las pruebas unitarias e integrales disponibles a la fecha.

## 1. Autenticación y seguridad
- `test_auth_endpoints.py`: `/login` en escenarios de éxito, usuario deshabilitado, empresa inactiva y cookie `remember_me`.
- `test_auth_change_password.py`: `change_password_direct` (éxito, contraseña actual incorrecta, reutilización y cooldown).
- `test_auth_password_reset_endpoints.py`: flujo "olvidé mi contraseña" (solicitud, verificación de token, confirmación con token válido o usado).
- `test_services_password_reset.py` y `test_services_utils.py`: utilidades de tokens, historial de contraseñas, fallback del chatbot y sanitización de respuestas.

## 2. Google OAuth
- `test_google_auth_routes.py`: `/auth/google/login`, callback (usuario inexistente, deshabilitado, empresa desactivada, éxito), `/auth/google/register-pending` y `/auth/google/logout-google`.

## 3. Chat y Voz
- `test_chat_routes.py`: endpoint `/chat/` y manejo de errores.
- `test_voice_routes.py`: `/api/voice/transcribe`, `/synthesize`, `/synthesize-base64`, `/voice/status`, `/voice/test` y `/voice/chat` (audio, history JSON inválido, texto > 5000).

## 4. Administración del Polo (`admin_users`)
- `test_admin_users_routes.py`:
  - Límites de creación de admin_empresa, detalle del polo, activación/desactivación de empresas.
  - CRUD de empresas, servicios del polo y lotes.
  - Búsquedas públicas (`/search`, `/search/contactos`, `/search/lotes`, `/all`).
  - `/usuarios/limits-status`, `/polo/change-password-request`, listados `/usuarios`, `/serviciopolo`, `/lotes`, `/roles`, consulta `/usuarios/{id}`.
- `test_admin_users.py`: cobertura adicional para creación/actualización de usuarios desde la vista del admin del polo, validando límites y restricciones únicas con SQLite en memoria.

## 5. Usuario empresa (`company_user`)
- `test_company_user_endpoints.py`: actualización de contraseña, y CRUD de vehículos, servicios y contactos para la empresa logueada.

## 6. Catálogos / Tipos
- `test_tipos_routes.py`: verificación de las funciones de `/tipos/*` utilizando objetos dummy.

## 7. Integración y otros endpoints
- `test_app_endpoints.py`: `/`, `/health` y estado de voz.
- `backend/tests/integration/test_db_metadata.py`: validación del inspector de metadatos de la base de datos.
- `backend/tests/integration/test_google_speech.py`: smoke tests del pipeline de voz contra Google Speech/TTS cuando las credenciales están configuradas.
- El resto de los archivos (`test_chat_routes.py`, `test_voice_routes.py`, `test_google_auth_routes.py`, etc.) completan la cobertura funcional.

## Resumen actual
- Resultado de la suite: `71 passed, 2 skipped, 89 warnings` (warnings conocidos por dependencias SSL/bcrypt, sin fallos).
