# Funcionalidades del backend (Polo 52)

Qué puede hacer cada rol del sistema, explicado en detalle. Al final hay un anexo técnico con la tabla de endpoints para referencia rápida.

## Los 3 roles del sistema

- **`admin_polo`**: el equipo de administración del Parque Industrial Polo 52. Gestiona todas las empresas instaladas, sus usuarios, los servicios propios del Polo (seguridad, bomberos, etc.) y los lotes. Solo puede haber usuarios `admin_polo` pertenecientes a la empresa "Parque Industrial Polo 52" — sin límite de cantidad.
- **`admin_empresa`**: el representante de una empresa instalada en el parque. Gestiona únicamente los datos de SU PROPIA empresa (vehículos, servicios que ofrece, contactos, ficha comercial). Nunca puede pertenecer a la empresa del Polo. Sin límite de cantidad de usuarios por empresa.
- **`publico`**: usuarios finales que usan el tótem/kiosco del parque. Solo pueden chatear con el asistente virtual y consultar el directorio de empresas — no gestionan nada. **Solo pueden crearse en la empresa del Polo** (el tótem/kiosco es del Polo, no de cada empresa instalada) — si se intenta crear un usuario `publico` con el CUIL de otra empresa, la API lo rechaza con un 400. Sin límite de cantidad.

---

## Rol `admin_polo` — qué puede hacer

### Su propio perfil (el Polo como entidad)
- Ver y editar los datos del Polo (`GET`/`PUT /polo/me`): cantidad de empleados, horario de trabajo y observaciones. El nombre, rubro y CUIL no son editables desde acá.
- Ver y cargar la **ficha comercial del Polo** (`GET`/`PUT /polo/comercial`): productos/servicios que ofrece el parque, público objetivo, rango de precios, modalidad de venta, etc. A diferencia de las empresas, el Polo no completa esto con un wizard de preguntas — el admin_polo carga todo directo en un formulario, y queda marcado como completado automáticamente al guardar.
- Solicitar el cambio de su propia contraseña (`POST /polo/change-password-request`).

### Gestión de empresas
- Listar todas las empresas del parque (`GET /empresas`).
- Actualizar nombre, rubro, estado, cantidad de empleados, observaciones y horario de una empresa puntual (`PUT /empresas/{cuil}`) — es el único rol que puede tocar estos campos de una empresa ajena.
- **Desactivar una empresa** (`PUT /empresas/{cuil}/desactivar`): hace baja lógica de la empresa Y de todo lo asociado a ella en cascada — sus usuarios, sus vehículos, sus servicios propios, sus contactos y sus servicios del Polo quedan todos inactivos al mismo tiempo. Es reversible.
- **Reactivar una empresa** (`PUT /empresas/{cuil}/activar`): el proceso inverso, reactiva la empresa y todo lo que se había desactivado con ella.

### Solicitudes de autoregistro
Cuando una empresa se autoregistra por `/register` (ver más abajo, sección pública), queda pendiente de aprobación. El admin_polo:
- Ve la lista de solicitudes pendientes (`GET /empresas/solicitudes`), con los datos de la empresa y de su usuario administrador.
- **Aprueba** una solicitud (`POST /empresas/{cuil}/aprobar`): activa la empresa y su usuario, y le manda un email avisándole que ya puede ingresar. También sirve para revertir un rechazo anterior.
- **Rechaza** una solicitud (`POST /empresas/{cuil}/rechazar`): la empresa queda marcada como rechazada (sigue inactiva, no se borra nada), y se le avisa por email al solicitante.

### Gestión de usuarios
- Listar todos los usuarios del sistema (`GET /usuarios`) y ver el detalle de uno puntual (`GET /usuarios/{id}`).
- **Crear usuarios nuevos** (`POST /usuarios`) — sin límite de cantidad para ningún rol, pero con reglas sobre a qué empresa puede pertenecer cada rol:
  - `admin_polo`: solo se puede crear para la empresa del Polo.
  - `admin_empresa`: **no se puede crear desde acá** — se crea automáticamente cuando una empresa se autoregistra (`/register`) y se aprueba. Si se intenta crear uno a mano, la API lo rechaza.
  - `publico`: solo se pueden crear para la empresa del Polo (son los usuarios que usan los tótems/kioscos).
  - La contraseña se genera automáticamente y se manda por email de bienvenida al usuario creado.
- Actualizar el estado (activo/inactivo) o resetear la contraseña de un usuario existente (`PUT /usuarios/{id}`).
- **Inhabilitar** un usuario (`DELETE /usuarios/{id}`) — no lo borra de la base, solo lo marca como inactivo (no puede loguearse más).
- Ver el listado de roles disponibles en el sistema (`GET /roles`).

### Servicios del Polo y lotes
- Listar los servicios propios del Polo (seguridad, bomberos, patrulla rural, etc.) (`GET /serviciopolo`).
- Crear un servicio del Polo nuevo, asociado a una empresa dueña (`POST /serviciopolo`) y eliminarlo (`DELETE /serviciopolo/{id}`).
- Listar todos los lotes registrados (`GET /lotes`).
- Crear un lote asociado a un servicio del Polo (`POST /lotes`), editarlo — típicamente para cargarle la ubicación en Google Maps (latitud/longitud) — (`PUT /lotes/{id}`), y eliminarlo (`DELETE /lotes/{id}`).

---

## Rol `admin_empresa` — qué puede hacer

Todo lo que hace este rol está scopeado automáticamente a **su propia empresa** (la que corresponde al `cuil` de su usuario) — nunca puede tocar datos de otra empresa.

### Su perfil y contraseña
- Cambiar su propia contraseña (`PUT /update_password`), con verificación de que no esté reutilizando una anterior.
- Ver todos los datos de su empresa, incluyendo vehículos, servicios, contactos y servicios del Polo asociados (`GET /me`).
- Actualizar los datos editables de su empresa: cantidad de empleados, observaciones y horario de trabajo (`PUT /companies/me`).

### Vehículos de la empresa
CRUD completo (`POST`/`PUT`/`DELETE /vehiculos[/{id}]`), con validación según el tipo de vehículo:
- **Corporativo**: requiere cantidad, patente y nivel de carga (baja/mediana/alta).
- **Personal**: requiere cantidad y patente.
- **De terceros**: requiere cantidad y nivel de carga.

### Servicios propios de la empresa
CRUD completo (`POST`/`PUT`/`DELETE /servicios[/{id}]`) — los servicios que la empresa ofrece a otras empresas del parque (no confundir con los "servicios del Polo", que administra admin_polo).

### Contactos de la empresa
CRUD completo (`POST`/`PUT`/`DELETE /contactos[/{id}]`) — nombre, teléfono, dirección y datos adicionales (redes, email, etc.) por tipo de contacto (comercial, empresarial).

### Catálogos
Consulta de los catálogos que alimentan los formularios de arriba: tipos de vehículo, tipos de servicio, tipos de contacto (`GET /tipos/vehiculo`, `/tipos/servicio`, `/tipos/contacto`).

### Información comercial (para que el chatbot público pueda responder consultas comerciales)
- Ver la ficha comercial ya cargada, o su estado parcial (`GET /companies/me/comercial`).
- **Wizard guiado** (`POST /companies/me/comercial/chat`): un cuestionario de 9 preguntas que se completan de a una por mensaje (productos/servicios, público objetivo, si atiende al público, horario comercial, rango de precios, modalidad de venta, marcas representadas, certificaciones, observaciones). No usa IA — es un flujo determinístico que valida y guarda cada respuesta antes de pasar a la siguiente pregunta.
- Editar campos puntuales de la ficha una vez completada, sin tener que repetir el wizard (`PUT /companies/me/comercial`).

---

## Rol `publico` — qué puede hacer

Pensado para los usuarios del tótem/kiosco físico del parque (o cualquier visitante logueado con este rol).

### Asistente virtual (chatbot con IA)
- Consultar el estado de los servicios de voz disponibles (`GET /api/voice/status`).
- **Hablar con el asistente** (`POST /api/voice/chat`): manda texto o audio, el bot responde con texto y audio (usando Gemini para entender la consulta + una base de datos de solo lectura, y Google Cloud para voz). Cada intercambio (lo que dijo el usuario y lo que respondió el bot) queda guardado automáticamente.
- **Ver el historial de conversaciones anteriores** (`GET /api/voice/history`): trae toda la charla previa del usuario, en orden cronológico, para que no se pierda al volver a entrar.
- Variantes puntuales: solo transcribir audio a texto (`POST /transcribe`), solo convertir texto a audio (`POST /synthesize` o `/synthesize-base64`), o pedir la respuesta en streaming de texto sin audio (`POST /chat/stream`).

### Directorio de empresas
- Ver el directorio completo de empresas activas del parque, con su contacto comercial y datos comerciales, pensado para que las empresas hagan networking entre sí (`GET /empresas/directorio`).
- Buscar empresas por nombre, rubro o tipo de servicio del Polo (`GET /search`).
- Buscar puntualmente los contactos o los lotes de una empresa por nombre (`GET /search/contactos`, `GET /search/lotes`).

> Nota: el directorio y la búsqueda están disponibles para **cualquier usuario logueado**, no solo `publico` — un admin_polo o admin_empresa también puede usarlos.

---

## Lo que se puede hacer sin estar logueado

- **Autoregistrar una empresa nueva** (`POST /register`): crea la empresa y su primer usuario `admin_empresa` juntos, ambos pendientes de aprobación por admin_polo. No hay login automático — recién puede entrar una vez aprobado.
- **Recuperar contraseña olvidada**: pedir el email de recuperación (`POST /forgot-password`), validar el link recibido (`POST /password-reset/verify-token`) y confirmar la nueva contraseña (`POST /forgot-password/confirm`).
- **Login con Google** (`/auth/google/login` → `/auth/google/callback`): alternativa al login con usuario/contraseña, usando la cuenta de Google. Si el email no está registrado, permite completar un autoregistro pendiente (`/auth/google/register-pending`).
- **Consultar los catálogos** de tipos de vehículo, servicio, contacto y servicio del Polo (`GET /tipos/*`) — pensado para poblar formularios incluso antes de loguearse (p. ej. en la pantalla de registro).

---

## Anexo técnico: tabla de endpoints

### Autenticación (`app/routes/auth.py`)

| Método | Path | Rol requerido | Descripción |
|---|---|---|---|
| POST | `/register` | público | Autoregistro de empresa + usuario admin_empresa (rate limit 5/min) |
| POST | `/login` | público | Login con usuario/contraseña → JWT (rate limit 10/min) |
| POST | `/logout` | logueado | Cerrar sesión |
| POST | `/bienvenida-vista` | logueado | Marcar como visto el aviso de bienvenida del primer login |
| POST | `/change-password-direct` | logueado | Cambiar contraseña sabiendo la actual |
| POST | `/forgot-password` | público | Solicitar reset de contraseña por email (rate limit 5/min) |
| POST | `/password-reset/verify-token` | público | Validar token de reset recibido por email |
| POST | `/forgot-password/confirm` | público | Confirmar nueva contraseña con token |
| POST | `/password-reset/confirm-secure` | público | Variante segura de confirmación de reset |
| POST | `/password-reset/cleanup-cache` | admin | Limpiar caché interno de tokens de reset |
| GET | `/password-reset/cache-status` | admin | Ver estado del caché de tokens de reset |

### Admin Polo (`app/routes/admin_users.py`) — todo el router requiere rol `admin_polo`

| Método | Path | Descripción |
|---|---|---|
| GET | `/polo/me` | Datos completos del Polo (empresa, servicios, usuarios, lotes) |
| PUT | `/polo/me` | Actualizar datos editables del Polo |
| GET | `/polo/comercial` | Ver ficha comercial cargada del Polo |
| PUT | `/polo/comercial` | Cargar/editar la ficha comercial del Polo (upsert directo, sin wizard) |
| POST | `/polo/change-password-request` | Solicitar cambio de contraseña propio |
| GET | `/empresas` | Listar todas las empresas |
| GET | `/usuarios` | Listar todos los usuarios |
| GET | `/usuarios/{user_id}` | Ver un usuario específico |
| POST | `/usuarios` | Crear usuario (contraseña autogenerada) |
| PUT | `/usuarios/{user_id}` | Actualizar usuario |
| DELETE | `/usuarios/{user_id}` | Inhabilitar usuario |
| GET | `/roles` | Listar roles disponibles |
| PUT | `/empresas/{cuil}` | Actualizar nombre/rubro/estado de una empresa |
| PUT | `/empresas/{cuil}/desactivar` | Desactivar empresa y sus registros asociados |
| PUT | `/empresas/{cuil}/activar` | Reactivar empresa y sus registros asociados |
| GET | `/empresas/solicitudes` | Listar solicitudes de registro pendientes |
| POST | `/empresas/{cuil}/aprobar` | Aprobar una solicitud de registro |
| POST | `/empresas/{cuil}/rechazar` | Rechazar una solicitud de registro |
| GET | `/serviciopolo` | Listar servicios del Polo |
| POST | `/serviciopolo` | Crear servicio del Polo |
| DELETE | `/serviciopolo/{id}` | Eliminar servicio del Polo |
| GET | `/lotes` | Listar todos los lotes |
| POST | `/lotes` | Crear lote asociado a un servicio del Polo |
| PUT | `/lotes/{id}` | Actualizar lote (p. ej. ubicación en Maps) |
| DELETE | `/lotes/{id}` | Eliminar lote |

### Admin Empresa (`app/routes/company_user.py`) — cada ruta exige `admin_empresa`

| Método | Path | Descripción |
|---|---|---|
| PUT | `/update_password` | Actualizar la contraseña del usuario logueado |
| GET | `/me` | Datos completos de la empresa propia |
| PUT | `/companies/me` | Actualizar datos propios (cant. empleados, observaciones, horario) |
| POST/PUT/DELETE | `/vehiculos[/{id}]` | CRUD de vehículos de la empresa |
| POST/PUT/DELETE | `/servicios[/{id}]` | CRUD de servicios propios de la empresa |
| POST/PUT/DELETE | `/contactos[/{id}]` | CRUD de contactos de la empresa |
| GET | `/tipos/vehiculo` \| `/tipos/servicio` \| `/tipos/contacto` | Catálogos para los formularios anteriores |
| GET | `/companies/me/comercial` | Ver ficha comercial cargada (o parcial) |
| PUT | `/companies/me/comercial` | Editar ficha comercial ya cargada |
| POST | `/companies/me/comercial/chat` | Wizard guiado que completa la ficha comercial |

### Directorio (`app/routes/directory.py`) — cualquier usuario logueado

| Método | Path | Descripción |
|---|---|---|
| GET | `/empresas/directorio` | Directorio de empresas (nombre, contacto comercial, teléfono, info comercial) |
| GET | `/search` | Buscar empresas por criterios |
| GET | `/search/contactos` | Buscar contactos por empresa |
| GET | `/search/lotes` | Buscar lotes por empresa |

### Catálogos (`app/routes/tipos.py`, prefix `/tipos`) — público, sin auth

| Método | Path | Descripción |
|---|---|---|
| GET | `/tipos/vehiculo` \| `/servicio` \| `/contacto` \| `/servicio-polo` | Catálogos usados en formularios de alta |

### Login con Google (`app/routes/google_auth.py`, prefix `/auth/google`)

| Método | Path | Descripción |
|---|---|---|
| GET | `/login` | Inicia el flujo OAuth2/OIDC con Google |
| GET | `/callback` | Callback de Google, arma la sesión |
| POST | `/register-pending` | Completa el registro de una empresa iniciado vía Google |
| POST | `/logout-google` | Logout del flujo de Google |

### Chatbot de texto (`app/routes/chat.py`, prefix `/chat`) — sin auth

| Método | Path | Descripción |
|---|---|---|
| POST | `/` | Chat de texto plano (sin voz) contra Gemini + DB |

> ⚠️ **Código muerto**: el frontend actual no llama a este endpoint (usa `/api/voice/chat` para todo, texto y voz).

### Voz + Chat IA principal (`app/routes/voice.py`, prefix `/api/voice`) — requiere estar logueado (cualquier rol)

> ⚠️ **Inconsistencia detectada**: el router exige `Depends(get_current_user)`, no `require_public_role` — cualquier usuario autenticado (`admin_polo`, `admin_empresa` o `publico`) puede usar el chatbot por API, aunque el frontend solo deja navegar a `/chat` a usuarios con rol `publico` (guard de ruta). No es una falla de autenticación (sigue exigiendo JWT válido), pero si la intención es que el chatbot sea exclusivo del rol `publico`, falta reforzarlo en el backend.

| Método | Path | Descripción |
|---|---|---|
| GET | `/status` | Estado de los servicios de voz (Google Speech/TTS) |
| POST | `/transcribe` | Transcribir audio a texto (solo STT) |
| POST | `/synthesize` | Convertir texto a audio (streaming MP3) |
| POST | `/synthesize-base64` | Igual que `/synthesize` pero devuelve base64 |
| POST | `/chat` | **Endpoint principal**: recibe texto o audio, responde con texto+audio, y guarda el turno en `chat_mensaje` |
| POST | `/chat/stream` | Streaming de la respuesta de texto (sin audio) |
| GET | `/history` | Historial completo de la conversación del usuario logueado, en orden cronológico |
| GET | `/test` | Test end-to-end del pipeline de voz (TTS + chat) |

### Endpoints raíz (`app/main.py`)

| Método | Path | Descripción |
|---|---|---|
| GET | `/` | Info general de la API |
| GET | `/health` | Health check (DB, Gemini, proveedor de voz) |

### Servicios internos (no HTTP, usados por las rutas de arriba)

- `app/services/chatbot_service.py`: pipeline texto → SQL de solo lectura vía Gemini, con whitelist/blacklist de tablas.
- `app/services/comercial_chatbot_service.py`: wizard determinístico (sin IA) que completa la ficha comercial de una empresa, un campo por mensaje.
- `app/services/voice_service.py`: wrappers de Google Cloud Speech-to-Text y Text-to-Speech.
- `app/services/email_service.py`: envío de emails transaccionales por SMTP (reset de contraseña, bienvenida, aprobación/rechazo de registro, etc.).
- `app/services/auth_service.py`: emisión/validación de JWT, hashing de contraseñas, generación de tokens de reset y control de historial de contraseñas.
- `app/services/common.py`: mensajes/constantes compartidos entre servicios.
- `app/rate_limit.py`: rate limiting propio en memoria por IP.
- `app/bootstrap.py`: crea tablas, siembra catálogos de referencia y el usuario `admin_polo` inicial al arrancar.
