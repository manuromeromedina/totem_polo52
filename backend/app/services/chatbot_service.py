# app/services/chatbot_service.py
import json
import os
import re
import unicodedata
from datetime import date
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing_extensions import TypedDict

from app.services.common import GENERIC_ERROR_MESSAGE
from app.services.voice_service import text_to_speech, transcribe_audio

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# ═══════════════════════════════════════════════════════════════════
# MODELO GEMINI: selección resiliente
# ═══════════════════════════════════════════════════════════════════
# En vez de "probar" nombres de modelo solo al construir el cliente (lo cual
# nunca detecta un modelo deprecado, porque el constructor no hace ninguna
# llamada de red), se prueba en la primera llamada real y, si el modelo activo
# fue dado de baja por Google, se pasa automáticamente al siguiente candidato
# y ese pasa a ser el modelo por defecto para el resto del proceso.
_MODEL_CANDIDATES = [
    os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]

_active_model_index = 0
_model_instances: Dict[str, "genai.GenerativeModel"] = {}


def _get_model_instance(name: str) -> "genai.GenerativeModel":
    if name not in _model_instances:
        _model_instances[name] = genai.GenerativeModel(model_name=name)
    return _model_instances[name]


def _generate(prompt: str, generation_config: GenerationConfig):
    """Genera contenido con el modelo activo, migrando de candidato si falla."""
    global _active_model_index

    seen = set()
    last_error = None
    idx = _active_model_index
    while idx < len(_MODEL_CANDIDATES):
        name = _MODEL_CANDIDATES[idx]
        if name in seen:
            idx += 1
            continue
        seen.add(name)
        try:
            response = _get_model_instance(name).generate_content(
                prompt, generation_config=generation_config
            )
            if idx != _active_model_index:
                print(
                    f"⚠️  Modelo Gemini '{_MODEL_CANDIDATES[_active_model_index]}' no disponible, "
                    f"usando '{name}' de ahora en más."
                )
                _active_model_index = idx
            return response
        except Exception as exc:
            print(f"  Modelo Gemini '{name}' falló: {exc}")
            last_error = exc
            idx += 1

    raise RuntimeError("Ningún modelo de Gemini disponible") from last_error


class _IntentSchema(TypedDict):
    needs_more_info: bool
    sql_query: str
    direct_answer: str
    corrected_entity: str
    question: str


INTENT_GENERATION_CONFIG = GenerationConfig(
    temperature=0.2,
    top_p=0.9,
    max_output_tokens=300,
    candidate_count=1,
    response_mime_type="application/json",
    response_schema=_IntentSchema,
)

FINAL_GENERATION_CONFIG = GenerationConfig(
    temperature=0.4,
    top_p=0.9,
    max_output_tokens=400,
    candidate_count=1,
)

# ═══════════════════════════════════════════════════════════════════
# POLÍTICA DE DATOS Y VALIDACIÓN SQL
# ═══════════════════════════════════════════════════════════════════

FORBIDDEN_SQL_TABLES = {
    "usuario",
    "rol",
    "rol_usuario",
    "vehiculos",
    "tipo_vehiculo",
    "empresa_vehiculos",
    "servicio",
    "tipo_servicio",
    "empresa_servicio",
    "password_history",
    "chat_mensaje",
}

# CUIL con el que se guarda la ficha comercial del propio Parque Industrial
# Polo 52 dentro de 'info_comercial' (misma tabla que usan las empresas).
# Ver app/routes/admin_users.py: POLO_CUIL.
POLO_CUIL = int(os.getenv("POLO_CUIL", "44123456789"))

FORBIDDEN_RESPONSE_TEXT = "No tengo permitido compartir esta información."

# Defensa en profundidad: el modelo solo debería generar un único SELECT,
# pero si un mensaje del usuario lograra manipularlo (prompt injection) para
# devolver sentencias apiladas ("SELECT ...; DROP TABLE ...;") o DDL/DML,
# esto lo corta antes de que llegue a execute_sql_query.
_FORBIDDEN_SQL_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate", "grant",
    "revoke", "create", "commit", "rollback", "begin", "exec", "execute",
    "call", "copy", "vacuum", "attach", "detach", "pragma",
}


def is_sql_query_allowed(sql_query: str) -> bool:
    """Validar que sea un único SELECT, sin sentencias apiladas ni tablas restringidas."""
    if not sql_query:
        return False

    stripped = sql_query.strip()
    if not stripped.lower().startswith("select"):
        return False

    # Sin sentencias apiladas: como mucho un ";" al final de la cadena.
    body = stripped[:-1] if stripped.endswith(";") else stripped
    if ";" in body:
        return False

    # Sin comentarios SQL (vector clásico para ocultar sentencias apiladas).
    if "--" in body or "/*" in body:
        return False

    normalized = re.sub(r"\s+", " ", body.lower()).replace('"', "").replace("'", "")

    for keyword in _FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized):
            return False

    for table in FORBIDDEN_SQL_TABLES:
        if re.search(rf"\b{table}\b", normalized):
            return False

    return True


def normalize_text(text_value: str) -> str:
    """Normalizar texto eliminando acentos y convirtiendo a minúsculas"""
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", text_value) if unicodedata.category(c) != "Mn"
    )
    return normalized.lower().strip()


def sanitize_response_text(text_value: Optional[str]) -> Optional[str]:
    """Limpiar la respuesta antes de devolverla al usuario."""
    if text_value is None:
        return None

    sanitized = text_value.replace("•", "-")
    sanitized = re.sub(r"\*+", "", sanitized)
    sanitized = re.sub(r"\s+\n", "\n", sanitized)
    return sanitized.strip()


def execute_sql_query(db: Session, query: str) -> List[Dict]:
    """Ejecutar consulta SQL de forma segura (solo SELECT)"""
    try:
        if not query.strip().lower().startswith("select"):
            print(f"Consulta no permitida: {query}")
            return [{"error": GENERIC_ERROR_MESSAGE}]
        result = db.execute(text(query), execution_options={"no_cache": True})
        columns = result.keys()
        raw_results = [dict(zip(columns, row)) for row in result.fetchall()]
        print(f"Resultados crudos de la consulta: {raw_results}")
        return raw_results
    except Exception as e:
        print(f"Error al ejecutar la consulta SQL: {str(e)}")
        return [{"error": GENERIC_ERROR_MESSAGE}]


# ═══════════════════════════════════════════════════════════════════
# ESQUEMA DE BASE DE DATOS (cacheado en memoria del proceso)
# ═══════════════════════════════════════════════════════════════════

_schema_cache: Optional[str] = None


def get_database_schema(db: Session, force_refresh: bool = False) -> str:
    """
    Obtener esquema de la base de datos para el chatbot.

    Se cachea en memoria: no hay migraciones en caliente en esta app (las
    tablas se crean una sola vez al arrancar), así que re-inspeccionar el
    esquema en cada mensaje del chat es puro overhead. `force_refresh=True`
    permite recalcularlo si alguna vez hiciera falta.
    """
    global _schema_cache
    if _schema_cache is not None and not force_refresh:
        return _schema_cache

    inspector = inspect(db.bind)
    schema = "La base de datos tiene las siguientes tablas, columnas y relaciones:\n"
    for table_name in inspector.get_table_names():
        if table_name.startswith(("pg_", "sql_")):
            continue
        if table_name.lower() in FORBIDDEN_SQL_TABLES:
            continue
        if table_name.lower().startswith("vw_"):
            continue

        schema += f"- Tabla '{table_name}':\n"
        for column in inspector.get_columns(table_name):
            schema += f"  - {column['name']} ({column['type'].__class__.__name__}"
            if column.get("primary_key"):
                schema += ", clave primaria"
            if column.get("nullable"):
                schema += ", nullable"
            schema += ")\n"
        for fk in inspector.get_foreign_keys(table_name):
            schema += (
                f"  Relación: '{table_name}.{fk['constrained_columns'][0]}' -> "
                f"'{fk['referred_table']}.{fk['referred_columns'][0]}'\n"
            )

    _schema_cache = schema
    return _schema_cache


def custom_json_serializer(obj):
    """Serializar objetos date para JSON"""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def extract_text_from_gemini(response) -> Optional[str]:
    """
    Obtener texto de forma segura desde una respuesta de Gemini.

    El acceso directo a `response.text` puede fallar cuando el modelo
    corta la generación por motivos de seguridad. Esta función intenta
    recuperar texto válido recorriendo los candidatos devueltos.
    """
    if response is None:
        return None

    try:
        direct_text = getattr(response, "text", None)
        if direct_text:
            return str(direct_text)
    except ValueError:
        pass

    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        finish_reason = getattr(candidate, "finish_reason", None)
        finish_str = str(finish_reason).lower() if finish_reason else ""
        if "safety" in finish_str or "blocked" in finish_str:
            continue

        content = getattr(candidate, "content", None)
        if not content:
            continue

        parts = getattr(content, "parts", None) or []
        fragments: List[str] = []
        for part in parts:
            part_text = getattr(part, "text", None)
            if not part_text and isinstance(part, dict):
                part_text = part.get("text")
            data = getattr(part, "data", None)
            if not part_text and isinstance(data, dict):
                part_text = data.get("text")
            if part_text:
                fragments.append(str(part_text))

        if fragments:
            combined = "\n".join(fragments).strip()
            if combined:
                return combined
    return None


def compose_fallback_response(db_results: List[Dict]) -> Optional[str]:
    """
    Generar una respuesta simple basada directamente en los datos obtenidos.
    Útil cuando el modelo no devuelve texto pero ya contamos con resultados.
    """
    if not db_results:
        return None

    if isinstance(db_results[0], dict) and db_results[0].get("error"):
        return None

    visible_rows = db_results[:6]
    total = len(db_results)

    formatted_rows: List[str] = []
    for row in visible_rows:
        if not isinstance(row, dict):
            continue

        name_parts: List[str] = []
        detail_parts: List[str] = []

        for key, value in row.items():
            key_lower = key.lower()
            if key_lower in {"id", "cuil", "id_usuario", "id_empresa"}:
                continue
            if key_lower.startswith("id_") or key_lower.endswith("_id"):
                continue

            if value in (None, "", []):
                continue

            if isinstance(value, date):
                value = value.strftime("%Y-%m-%d")
            elif isinstance(value, (list, tuple, set)):
                value = ", ".join(str(item) for item in value if item not in (None, ""))
                if not value:
                    continue
            elif isinstance(value, dict):
                sub_parts = []
                for sub_key, sub_value in value.items():
                    if sub_value in (None, "", []):
                        continue
                    sub_label = sub_key.replace("_", " ").capitalize()
                    sub_parts.append(f"{sub_label}: {sub_value}")
                if not sub_parts:
                    continue
                value = ", ".join(sub_parts)

            if key_lower.startswith("nombre"):
                name_parts.append(str(value))
            else:
                label = key.replace("_", " ").capitalize()
                detail_parts.append(f"{label}: {value}")

        if not name_parts and not detail_parts:
            continue

        main_text = " ".join(name_parts) if name_parts else detail_parts.pop(0)
        if detail_parts:
            main_text = f"{main_text}. {'; '.join(detail_parts)}"

        formatted_rows.append(f"- {main_text}")

    if not formatted_rows:
        return None

    header = (
        f"Encontré {total} registros. Te comparto {min(total, len(visible_rows))} destacados:"
        if total > len(visible_rows)
        else f"Encontré {total} registros:"
    )
    formatted_rows.insert(0, header)
    return "\n".join(formatted_rows)


def parse_intent_json(response) -> Tuple[Optional[dict], Optional[str]]:
    """Extraer el JSON devuelto por Gemini en la etapa de intención."""
    raw_text = extract_text_from_gemini(response)
    if not raw_text:
        return None, None

    cleaned = raw_text.strip()
    if "```" in cleaned:
        cleaned = re.sub(r"```json|```", "", cleaned, flags=re.IGNORECASE).strip()

    try:
        return json.loads(cleaned), raw_text
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None, raw_text
        try:
            return json.loads(match.group(0)), raw_text
        except json.JSONDecodeError:
            return None, raw_text


# ═══════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL DEL CHATBOT
# ═══════════════════════════════════════════════════════════════════


def get_chat_response(db: Session, message: str, history: List[Dict[str, str]] = None):
    """Generar respuesta del chatbot usando Gemini AI"""
    try:
        user_input = normalize_text(message)
        chat_history = ""
        if history:
            for entry in history:
                if entry.get("user"):
                    chat_history += f"Usuario: {entry['user']}\n"
                if entry.get("assistant"):
                    chat_history += f"Asistente: {entry['assistant']}\n"

        db_schema = get_database_schema(db)

        intent_prompt = f"""
Eres POLO, asistente del Parque Industrial Polo 52.

Base de datos disponible:
{db_schema}

Historial:
{chat_history}

Consulta del usuario (texto libre normalizado): "{user_input}"

Para comparaciones de texto, usa siempre ILIKE en lugar de = para hacer búsquedas.
Tu inteligencia artificial debe SIEMPRE intentar responder con datos reales. Debes hacer la consulta SQL. Solo usa needs_more_info=true si es absolutamente imposible interpretar la consulta.

Política de datos:
- Solo puedes usar tablas relacionadas con empresas, servicios del parque, lotes, contactos e información comercial de las empresas (tabla 'info_comercial').
- Tienes prohibido consultar tablas: usuario, rol, rol_usuario, vehiculos, tipo_vehiculo, empresa_vehiculos, servicio, tipo_servicio, empresa_servicio, password_history, chat_mensaje.
- Si la consulta requiere información prohibida, devuelve sql_query como cadena vacía ("") y needs_more_info en false.
- La información disponible abarca detalles de empresas, los servicios y espacios del parque, lotes, contactos (incluye teléfono, dirección, web, correo y redes sociales de contactos comerciales) y datos comerciales (productos/servicios que vende cada empresa, público al que atiende, precios, modalidad de venta, marcas, certificaciones, etc.). Usa tu criterio para combinar la información relevante de estas fuentes y ofrecer respuestas útiles, incluyendo consultas comerciales sobre las empresas del parque.
- La tabla 'info_comercial' es información PÚBLICA y comercial por definición (nunca la trates como restringida): tiene como clave 'cuil', que referencia a 'empresa.cuil'. Para preguntas sobre la ficha comercial de una empresa puntual, hacé JOIN de 'empresa' con 'info_comercial' por cuil. El propio Parque Industrial Polo 52 también tiene su ficha comercial cargada en 'info_comercial' con cuil = {POLO_CUIL}: si preguntan por los servicios/propuesta comercial "del polo" (no de una empresa en particular), consultá esa fila puntual (WHERE cuil = {POLO_CUIL}).
- Si 'info_comercial' no tiene fila para una empresa, o campos en null, no es información prohibida: simplemente todavía no la cargaron. Respondé eso con naturalidad, nunca como si estuviera prohibida.

Completa los campos:
- needs_more_info: false (casi siempre, usa tu IA para interpretar)
- sql_query: consulta SQL para obtener datos (NUNCA incluyas campos como cuil, id en el SELECT). Si la consulta es solo un saludo, agradecimiento u otra interacción social que no requiera base de datos, deja este campo como cadena vacía.
- direct_answer: texto natural, breve (una o dos frases), para responder saludos, agradecimientos o mensajes sociales similares cuando no se requiera consultar la base. Cadena vacía si no aplica.
- corrected_entity: corrección si detectas errores de escritura en nombres propios. Cadena vacía si no aplica.
- question: pregunta de aclaración, solo si needs_more_info es true. Cadena vacía si no aplica.

Tu IA debe entender saludos, expresiones de cortesía, consultas informales o con errores de escritura y contestar de manera natural sin asumir información restringida.
"""

        try:
            intent_response = _generate(intent_prompt, INTENT_GENERATION_CONFIG)
            intent_data, raw_intent_text = parse_intent_json(intent_response)
        except Exception as e:
            print(f"Error generando intención: {str(e)}")
            intent_data, raw_intent_text = None, None

        if not intent_data:
            fallback_text = sanitize_response_text(raw_intent_text)
            if fallback_text:
                print("No se pudo interpretar el JSON de intención; devolviendo texto crudo del modelo.")
                return fallback_text, [], None
            print(f"Intent parse falló. Respuesta cruda: {raw_intent_text}")
            return "Disculpa, tuve un problema procesando tu consulta. ¿Podrías reformularla?", [], None

        if intent_data.get("needs_more_info", False):
            question = intent_data.get("question") or "¿Podrías darme más detalles sobre tu consulta?"
            return question, [], intent_data.get("corrected_entity")

        direct_answer = sanitize_response_text(intent_data.get("direct_answer"))
        sql_query = intent_data.get("sql_query", "")

        if direct_answer:
            return direct_answer, [], intent_data.get("corrected_entity")

        if not sql_query or not is_sql_query_allowed(sql_query):
            return FORBIDDEN_RESPONSE_TEXT, [], intent_data.get("corrected_entity")

        db_results = execute_sql_query(db, sql_query)
        if db_results and isinstance(db_results[0], dict) and db_results[0].get("error"):
            return GENERIC_ERROR_MESSAGE, [], intent_data.get("corrected_entity")

        # Nota: si db_results viene vacío, lo dejamos pasar igual a Gemini en
        # vez de devolver un mensaje fijo por código. El propio prompt ya le
        # indica cómo manejar la ausencia de resultados, y así lo resuelve
        # con criterio propio en vez de una frase enlatada siempre igual.
        results_text = json.dumps(db_results, ensure_ascii=False, default=custom_json_serializer)
        input_text = f"Resultados de la consulta:\n{results_text}\nPregunta:\n{message}"

        final_prompt = f"""
Eres POLO, asistente conversacional del Parque Industrial Polo 52.

Información disponible:
{input_text}

Historial:
{chat_history}

Reglas que no podés romper:
- Solo hablás de temas del Parque Industrial Polo 52 y de los datos que tenés disponibles. Si te preguntan algo ajeno, respondé: "Solo puedo ayudarte con información del Parque Industrial Polo 52."
- Nunca muestres CUIL, IDs internos ni datos sensibles.
- Si la consulta es sobre usuarios, contraseñas, roles o vehículos del sistema interno, respondé exactamente: "No tengo permitido compartir esta información". Esto NO aplica a información comercial (productos, servicios, precios, modalidad de venta, público al que atiende, marcas, certificaciones, contacto) de las empresas ni del propio Parque: esa información es pública y siempre podés compartirla con lo que tengas disponible.
- Si no hay resultados para la consulta, decilo con naturalidad y, si tiene sentido, ofrecé una alternativa relacionada con el parque.

Fuera de esas reglas, usá tu propio criterio: contestá de forma natural y breve (como en una conversación real, sin relleno), con el tono y formato que mejor se adapten a la pregunta.
Responde naturalmente:"""

        try:
            final_response = _generate(final_prompt, FINAL_GENERATION_CONFIG)
            final_text = sanitize_response_text(extract_text_from_gemini(final_response))
        except Exception as e:
            print(f"Error generando respuesta final: {str(e)}")
            final_text = None

        if not final_text:
            # Gemini no devolvió nada usable (bloqueo de seguridad, error de API, etc.):
            # como último recurso armamos algo a partir de los datos crudos.
            print("Advertencia: Gemini no devolvió texto utilizable en la respuesta final.")
            fallback_text = sanitize_response_text(compose_fallback_response(db_results))
            if fallback_text:
                return fallback_text, db_results, intent_data.get("corrected_entity")
            return GENERIC_ERROR_MESSAGE, db_results, intent_data.get("corrected_entity")

        return final_text, db_results, intent_data.get("corrected_entity")

    except Exception as e:
        print(f"Error general en get_chat_response: {str(e)}")
        return GENERIC_ERROR_MESSAGE, [], None


def get_chat_response_stream(
    db: Session,
    text_message: str,
    history: Optional[List[Dict[str, str]]] = None,
):
    """
    Variante en streaming: procesa intent + DB igual que get_chat_response,
    pero entrega la respuesta final en un solo chunk (Gemini no se re-llama
    para no duplicar costo/latencia).
    """
    final_text, db_results, corrected = get_chat_response(db=db, message=text_message, history=history)
    if final_text:
        yield final_text, db_results, corrected


def get_chat_response_with_audio(
    db: Session,
    audio_content: bytes = None,
    text_message: str = None,
    history: List[Dict[str, str]] = None,
) -> dict:
    """Procesar mensaje de voz o texto y devolver respuesta con audio"""
    from fastapi import HTTPException
    import base64

    try:
        transcript = None

        if audio_content:
            print(f" Procesando audio: {len(audio_content)} bytes")
            transcript = transcribe_audio(audio_content)

            if not transcript or len(transcript.strip()) == 0:
                error_message = GENERIC_ERROR_MESSAGE
                error_audio = text_to_speech(error_message)
                error_audio_base64 = base64.b64encode(error_audio).decode("utf-8")
                return {
                    "text": error_message,
                    "audio_base64": error_audio_base64,
                    "db_results": [],
                    "transcript": None,
                    "corrected_entity": None,
                    "error": True,
                }

            message = transcript
            print(f" Transcripción: {message}")
        elif text_message:
            message = text_message
            print(f" Mensaje de texto: {message}")
        else:
            raise HTTPException(status_code=400, detail="Se requiere audio o texto")

        print(" Procesando con Gemini...")
        response_text, db_results, corrected_entity = get_chat_response(db, message, history)
        print(f" Respuesta generada: {response_text[:100]}...")

        print("🔊 Generando audio de respuesta...")
        audio_bytes = text_to_speech(response_text)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        print(f" Audio generado: {len(audio_base64)} caracteres en base64")

        return {
            "text": response_text,
            "audio_base64": audio_base64,
            "db_results": db_results,
            "transcript": transcript,
            "corrected_entity": corrected_entity,
            "error": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error procesando consulta: {str(e)}"
        print(f" {error_msg}")
        try:
            error_response = GENERIC_ERROR_MESSAGE
            error_audio = text_to_speech(error_response)
            error_audio_base64 = base64.b64encode(error_audio).decode("utf-8")
            return {
                "text": error_response,
                "audio_base64": error_audio_base64,
                "db_results": [],
                "transcript": transcript,
                "corrected_entity": None,
                "error": True,
            }
        except Exception:
            raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


def test_voice_pipeline(db: Session, test_text: str = "Hola, soy POLO Bot del Parque Industrial Polo 52") -> dict:
    """Probar pipeline completo de voz (TTS + chatbot)"""
    results = {"text_to_speech": None, "chat_response": None, "errors": []}

    try:
        import base64

        audio_bytes = text_to_speech(test_text)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        results["text_to_speech"] = {
            "status": " OK",
            "audio_size_bytes": len(audio_bytes),
            "audio_base64_length": len(audio_base64),
        }
    except Exception as e:
        results["text_to_speech"] = {"status": " ERROR", "error": str(e)}
        results["errors"].append(f"TTS: {str(e)}")

    try:
        response_text, db_results, _ = get_chat_response(db, "¿Qué servicios ofrece el parque?", None)
        results["chat_response"] = {
            "status": " OK",
            "response_length": len(response_text),
            "db_results_count": len(db_results),
        }
    except Exception as e:
        results["chat_response"] = {"status": " ERROR", "error": str(e)}
        results["errors"].append(f"Chat: {str(e)}")

    results["summary"] = (
        " Todos los tests pasaron" if len(results["errors"]) == 0 else f" {len(results['errors'])} errores encontrados"
    )
    return results
