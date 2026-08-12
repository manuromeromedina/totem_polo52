# app/services/__init__.py
"""
Paquete de servicios del backend, separado por responsabilidad:

- common: constantes compartidas.
- auth_service: hashing, JWT, tokens de recuperación, historial de contraseñas.
- email_service: envío de emails (bienvenida, notificaciones).
- voice_service: Speech-to-Text / Text-to-Speech (Google Cloud).
- chatbot_service: pipeline del chatbot con Gemini.

Todo se re-exporta acá para que el resto del código siga usando
`from app import services; services.hash_password(...)` o
`from app.services import get_chat_response` sin cambios.
"""
from fastapi import HTTPException  # re-exportado: algunos tests lo referencian como services.HTTPException

from app.services.common import GENERIC_ERROR_MESSAGE

from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    USED_RESET_TOKENS,
    check_token_validity,
    cleanup_used_tokens,
    consume_password_reset_token,
    create_access_token,
    create_password_reset_token,
    forgot_password_reset_confirm,
    generate_random_password,
    get_used_tokens_count,
    hash_password,
    is_password_reused,
    is_token_already_used,
    mark_token_as_used,
    pwd_context,
    save_password_to_history,
    secure_password_reset_confirm,
    verify_password,
    verify_password_reset_token,
)

from app.services.email_service import (
    send_admin_password_change_request_email,
    send_password_change_failure_notification,
    send_password_change_notification,
    send_password_reset_email,
    send_welcome_email,
)

from app.services import voice_service
from app.services.voice_service import (
    VOICE_PROVIDER,
    speech_client,
    text_to_speech,
    text_to_speech_google,
    tts_client,
    transcribe_audio,
    transcribe_audio_google,
    get_voice_services_status,
)

from app.services import chatbot_service
from app.services.chatbot_service import (
    FORBIDDEN_RESPONSE_TEXT,
    FORBIDDEN_SQL_TABLES,
    compose_fallback_response,
    custom_json_serializer,
    execute_sql_query,
    extract_text_from_gemini,
    get_chat_response,
    get_chat_response_stream,
    get_chat_response_with_audio,
    get_database_schema,
    is_sql_query_allowed,
    normalize_text,
    parse_intent_json,
    sanitize_response_text,
    test_voice_pipeline,
)

from app.services import comercial_chatbot_service
from app.services.comercial_chatbot_service import (
    QUESTIONS as COMERCIAL_CHAT_QUESTIONS,
    get_comercial_chat_response,
)
