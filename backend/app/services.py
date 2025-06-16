import unicodedata
import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from sqlalchemy.sql import text
from fastapi import HTTPException

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config import SECRET_KEY, ALGORITHM
from app.models import Empresa

import json
from datetime import date

# === 🔐 Cargar el archivo .env desde /backend ===
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# === 🔐 Configurar API Key ===
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# === ⚙️ Configurar el modelo Gemini ===
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config=GenerationConfig(
        temperature=0.3,
        top_p=0.9,
        max_output_tokens=1024,  # Aumentado para permitir respuestas más largas
        stop_sequences=None
    )
)

# === 🔒 Utilidades de autenticación ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def create_password_reset_token(email: str, expires_minutes: int = 60) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=expires_minutes)
    to_encode = {"sub": email, "exp": exp, "type": "password_reset"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 2) Verificar token de recuperación y devolver el email
def verify_password_reset_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            raise HTTPException(401, "Token de tipo inválido")
        email = payload.get("sub")
        if not email:
            raise HTTPException(401, "Token inválido")
        return email
    except JWTError:
        raise HTTPException(401, "Token de recuperación inválido o expirado")

def normalize_text(text: str) -> str:
    normalized = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return normalized.lower().strip()

def execute_sql_query(db: Session, query: str) -> List[Dict]:
    try:
        if not query.strip().lower().startswith("select"):
            print(f"Consulta no permitida: {query}")
            return [{"error": "Solo se permiten consultas SELECT."}]
        result = db.execute(text(query), execution_options={"no_cache": True})  # Deshabilitar caché
        columns = result.keys()
        raw_results = [dict(zip(columns, row)) for row in result.fetchall()]
        print(f"Resultados crudos de la consulta: {raw_results}")  # Log para depuración
        return raw_results
    except Exception as e:
        print(f"Error al ejecutar la consulta SQL: {str(e)}")
        return [{"error": f"Error al ejecutar la consulta: {str(e)}"}]

def get_database_schema(db: Session) -> str:
    inspector = inspect(db.bind)
    schema = "La base de datos tiene las siguientes tablas, columnas y relaciones:\n"
    for table_name in inspector.get_table_names():
        if not table_name.startswith(('pg_', 'sql_')):
            schema += f"- Tabla '{table_name}':\n"
            columns = inspector.get_columns(table_name)
            for column in columns:
                schema += f"  - {column['name']} ({column['type'].__class__.__name__}"
                if column.get('primary_key'):
                    schema += ", clave primaria"
                if column.get('nullable'):
                    schema += ", nullable"
                schema += ")\n"
            foreign_keys = inspector.get_foreign_keys(table_name)
            for fk in foreign_keys:
                schema += f"  Relación: '{table_name}.{fk['constrained_columns'][0]}' -> '{fk['referred_table']}.{fk['referred_columns'][0]}'\n"
    return schema

# Función auxiliar para manejar tipos no serializables
def custom_json_serializer(obj):
    if isinstance(obj, date):
        return obj.isoformat()  # Convierte datetime.date a formato ISO (por ejemplo, "2021-11-05")
    raise TypeError(f"Type {type(obj)} not serializable")

def get_chat_response(db: Session, message: str, history: List[Dict[str, str]] = None):
    try:
        # Normalizar y montar historial (sin cambios)
        user_input = normalize_text(message)
        chat_history = ""
        if history:
            for entry in history:
                if entry.get("user"):
                    chat_history += f"Usuario: {entry['user']}\n"
                if entry.get("assistant"):
                    chat_history += f"Asistente: {entry['assistant']}\n"

        # Obtener esquema (sin cambios)
        db_schema = get_database_schema(db)

        # ─── Prompt para generación de SQL ─────────────────────────────────────
        intent_prompt = (
            "Eres POLO, asistente del Parque Industrial Polo 52. "
            "Devuélveme **solo** un JSON válido (con **comillas dobles** en claves y valores), "
            "sin explicaciones extra. Debe tener siempre estas cuatro claves:\n"
            "  \"needs_more_info\"  (true|false),\n"
            "  \"sql_query\"        (string),\n"
            "  \"corrected_entity\" (string),\n"
            "  \"question\"         (string)\n"
            "Ejemplo:\n"
            "```json\n"
            "{\n"
            '  "needs_more_info": true,\n'
            '  "sql_query": "",\n'
            '  "corrected_entity": "",\n'
            '  "question": "¿Podrías indicar de qué empresa hablas?"\n'
            "}\n"
            "```\n\n"
            "Esquema de la base de datos:\n"
            + db_schema + "\n\n"
            "Historial de la conversación:\n"
            + chat_history + "\n\n"
            "Pregunta actual:\n"
            + user_input
        )
        intent_response = model.generate_content(intent_prompt)
        intent_data = json.loads(intent_response.text.strip("```json\n").strip("\n```"))

        # ─── Si faltan datos, uso siempre 'question' del JSON ─────────────────
        if intent_data.get("needs_more_info", False):
            return intent_data["question"], [], intent_data.get("corrected_entity")

        # ─── Ejecución de la query y chequeos (sin cambios) ───────────────────
        sql_query  = intent_data["sql_query"]
        db_results = execute_sql_query(db, sql_query)
        if not db_results or "error" in db_results[0]:
            return db_results[0].get("error", "Error interno"), [], intent_data.get("corrected_entity")

        # ─── Serializo resultados para el prompt final ────────────────────────
        results_text = json.dumps(db_results, ensure_ascii=False, default=custom_json_serializer)
        input_text   = f"Resultados de la consulta:\n{results_text}\nPregunta:\n{message}"

        # ─── Prompt para la respuesta final ───────────────────────────────────
        final_prompt = f"""
        Eres POLO, el asistente conversacional oficial del Parque Industrial Polo 52.
        1) Sólo saluda (“Hola, soy POLO, tu asistente…”) si:
        - Es la primera vez que pisas la conversación, o
        - El usuario empezó con un saludo (“hola”, “buenas”).
        2) Nunca uses “Sobre tu consulta”.
        3) Presenta la información en 1–2 párrafos fluidos, sin viñetas ni Markdown.  
        Incluye todos los datos relevantes (nombre, rubro, empleados, horarios, etc.),  
        pero **nunca** IDs ni CUIL.
        4) Integra la información de “Información de la consulta” de forma natural: explica qué datos obtuviste y qué significan.
        5) Si ves palabras de agradecimiento (“gracias”, “muy amable”), responde **una sola vez**:
        “¡De nada! Siempre a tu servicio.”
        6) Termina SIEMPRE con una pregunta abierta:  
        “¿Te gustaría saber algo más sobre otra empresa o servicio del parque?”


        Información disponible:
        {input_text}

        Historial:
        {chat_history}
    """
        final_response = model.generate_content(final_prompt)
        return final_response.text, db_results, intent_data.get("corrected_entity")

    except Exception as e:
        return f"Error al procesar el mensaje: {str(e)}", [], None