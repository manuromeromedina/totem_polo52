import unicodedata
import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from sqlalchemy.sql import text
from fastapi import HTTPException

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config import SECRET_KEY, ALGORITHM
from app.models import Empresa

# === 🔐 Cargar el archivo .env desde /backend ===
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# === 🔐 Configurar API Key ===
api_key = os.getenv("GOOGLE_API_KEY")
print(f"🔐 API Key cargada: {api_key}")
genai.configure(api_key=api_key)

# === ⚙️ Configurar el modelo Gemini ===
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config=GenerationConfig(
        temperature=0.2,
        top_p=1.0,
        max_output_tokens=512,
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

# === 🔤 Utilidades del chatbot ===
def normalize_text(text: str) -> str:
    normalized = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return normalized.lower().strip()

def execute_sql_query(db: Session, query: str) -> List[Dict]:
    try:
        if not query.strip().lower().startswith("select"):
            print(f"Consulta no permitida: {query}")
            return [{"error": "Solo se permiten consultas SELECT."}]
        result = db.execute(text(query))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
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

def get_chat_response(db: Session, message: str, history: List[Dict[str, str]] = None):
    try:
        user_input = normalize_text(message)
        print(f"Mensaje recibido: {message}")

        db_schema = get_database_schema(db)
        print(f"Esquema de la base de datos: {db_schema}")

        chat_history = ""
        if history:
            for entry in history:
                if entry.get("user"):
                    chat_history += f"Usuario: {entry['user']}\n"
                if entry.get("assistant"):
                    chat_history += f"Asistente: {entry['assistant']}\n"

        intent_prompt = (
            "Eres POLO, un asistente del Parque Industrial Polo 52. Tu objetivo es ayudar a los usuarios respondiendo preguntas sobre las empresas y datos relacionados del parque de manera fluida y natural. "
            "Se te proporcionará el esquema de la base de datos, el historial de la conversación y la pregunta actual del usuario. "
            "Tu tarea es:\n"
            "1. Analizar la pregunta del usuario y el historial para determinar la intención.\n"
            "2. Si hay errores de escritura, usá ILIKE para buscar coincidencias aproximadas.\n"
            "3. Si falta información clave, devolvé: {\"needs_more_info\": true, \"question\": \"...\"}\n"
            "4. Si no entendés, devolvé: {\"needs_more_info\": true, \"question\": \"...\"}\n"
            "5. Si todo está bien, generá la consulta SQL.\n"
            "6. Respondé con un JSON: {\"needs_more_info\": false, \"sql_query\": \"...\", \"corrected_entity\": \"...\"}\n\n"
            f"Esquema de la base de datos:\n{db_schema}\n\n"
            f"Historial de la conversación:\n{chat_history}\n\n"
            f"Pregunta actual del usuario: {user_input}"
        )

        intent_response = model.generate_content(intent_prompt)
        intent_text = intent_response.text
        print(f"Respuesta de Gemini (fase 1): {intent_text}")

        match = re.search(r"\{.*\}", intent_text, re.DOTALL)
        if not match:
            raise HTTPException(status_code=500, detail="No se pudo interpretar la respuesta del modelo.")
        intent_data = json.loads(match.group(0))

        if intent_data.get("needs_more_info", False):
            return intent_data["question"]

        sql_query = intent_data.get("sql_query")
        if not sql_query:
            return "No se pudo generar una consulta válida. ¿Podés reformular tu pregunta?"

        db_results = execute_sql_query(db, sql_query)
        print(f"Resultados SQL: {db_results}")

        if db_results and "error" in db_results[0]:
            return db_results[0]["error"]

        if not db_results:
            entity = intent_data.get("corrected_entity", "la entidad buscada")
            return f"No se encontraron datos para {entity}. ¿Querés preguntar sobre otra empresa o tema?"

        db_info = "\n".join([str(result) for result in db_results])

        final_prompt = (
            "Eres POLO, un asistente del Parque Industrial Polo 52. Tu objetivo es responder profesionalmente basándote en los datos proporcionados.\n"
            "1. Analizá los datos y respondé con claridad y buena redacción.\n"
            "2. Organizá por empresa o categoría si hay muchos datos.\n"
            "3. Indicá si hay campos vacíos.\n"
            "4. Terminá la respuesta ofreciendo más ayuda.\n\n"
            f"Datos obtenidos:\n{db_info}\n\n"
            f"Historial de la conversación:\n{chat_history}\n\n"
            f"Pregunta actual: {user_input}"
        )

        final_response = model.generate_content(final_prompt)
        return final_response.text

    except Exception as e:
        print(f"Error general: {str(e)}")
        return f"Ocurrió un error al procesar tu consulta: {str(e)}"
