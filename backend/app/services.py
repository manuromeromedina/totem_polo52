import unicodedata
import os
import json
import re
from typing import List, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from sqlalchemy.sql import text

from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from fastapi import HTTPException

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config import SECRET_KEY, ALGORITHM
from app.models import Empresa

import json
from datetime import date

# === Cargar el archivo .env desde /backend ===
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# === Utilidades de autenticación =============================================

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
    """
    Crear token de recuperación de contraseña con expiración personalizable
    
    Args:
        email: Email del usuario
        expires_minutes: Minutos hasta la expiración (default: 60 = 1 hora)
    """
    now = datetime.utcnow()
    exp = now + timedelta(minutes=expires_minutes)
    to_encode = {
        "sub": email, 
        "exp": exp, 
        "type": "password_reset",
        "iat": now  # Tiempo de emisión (issued at)
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password_reset_token(token: str) -> str:
    """
    Verificar token de recuperación y devolver el email
    
    Raises:
        HTTPException(400): Token expirado específicamente
        HTTPException(401): Token inválido por otras razones
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verificar que sea un token de reset
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=401, 
                detail="Token de tipo inválido"
            )
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=401, 
                detail="Token inválido - falta información del usuario"
            )
            
        return email
        
    except ExpiredSignatureError:
        # Token específicamente expirado
        raise HTTPException(
            status_code=400, 
            detail="El enlace de recuperación ha expirado. Solicita uno nuevo.",
            headers={"X-Error-Type": "expired"}
        )
    except JWTError as e:
        # Otros errores de JWT (token malformado, firma inválida, etc.)
        raise HTTPException(
            status_code=401, 
            detail="Token de recuperación inválido",
            headers={"X-Error-Type": "invalid"}
        )

# Función adicional para verificar token sin decodificar (opcional)
def check_token_validity(token: str) -> dict:
    """
    Verificar si un token es válido sin hacer operaciones críticas
    Útil para verificación previa en el frontend
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "valid": True,
            "email": payload.get("sub"),
            "expires_at": payload.get("exp"),
            "type": payload.get("type")
        }
    except ExpiredSignatureError:
        return {
            "valid": False,
            "error": "expired",
            "message": "Token expirado"
        }
    except JWTError:
        return {
            "valid": False,
            "error": "invalid",
            "message": "Token inválido"
        }
# =================================================================================

# === Configurar API Key ===
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# === CONFIGURACIÓN SIMPLE Y ROBUSTA ===
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config=GenerationConfig(
        temperature=0.3,
        top_p=0.9,
        max_output_tokens=1024,
        stop_sequences=None,
        candidate_count=1
    )
)

def normalize_text(text: str) -> str:
    normalized = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return normalized.lower().strip()

def execute_sql_query(db: Session, query: str) -> List[Dict]:
    try:
        if not query.strip().lower().startswith("select"):
            print(f"Consulta no permitida: {query}")
            return [{"error": "Solo se permiten consultas SELECT."}]
        result = db.execute(text(query), execution_options={"no_cache": True})
        columns = result.keys()
        raw_results = [dict(zip(columns, row)) for row in result.fetchall()]
        print(f"Resultados crudos de la consulta: {raw_results}")
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

def custom_json_serializer(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def get_chat_response(db: Session, message: str, history: List[Dict[str, str]] = None):
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

        # === PROMPT 100% IA - AGRESIVO EN INTERPRETACIÓN ===
        intent_prompt = f"""
Eres POLO, asistente del Parque Industrial Polo 52. 

Base de datos disponible:
{db_schema}

Historial:
{chat_history}

Consulta del usuario: "{user_input}"

Para comparaciones de texto, usa siempre ILIKE en lugar de = para hacer búsquedas
Tu inteligencia artificial debe SIEMPRE intentar responder con datos reales. Debes hacer la consulta SQL. Solo usa needs_more_info=true si es absolutamente imposible interpretar la consulta.

Responde con un JSON:
- needs_more_info: false (casi siempre, usa tu IA para interpretar)
- sql_query: consulta SQL para obtener datos (NUNCA incluyas campos como cuil, id en el SELECT)
- corrected_entity: corrección si detectas errores 
- question: pregunta solo si needs_more_info es true

Tu IA debe entender consultas informales, vagas o con errores de escritura. Interpreta con inteligencia lo que realmente necesita el usuario.

JSON:"""

        intent_response = model.generate_content(intent_prompt)

        
        try:
            clean_response = intent_response.text.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0]
            elif "```" in clean_response:
                clean_response = clean_response.replace("```", "")
            
            intent_data = json.loads(clean_response.strip())
        except (json.JSONDecodeError, IndexError):
            return "Disculpa, tuve un problema procesando tu consulta. ¿Podrías reformularla?", [], None

        if intent_data.get("needs_more_info", False):
            return intent_data["question"], [], intent_data.get("corrected_entity")

        sql_query = intent_data["sql_query"]
        db_results = execute_sql_query(db, sql_query)
        
        results_text = json.dumps(db_results, ensure_ascii=False, default=custom_json_serializer)
        input_text = f"Resultados de la consulta:\n{results_text}\nPregunta:\n{message}"

        # === RESPUESTA NATURAL Y DIRECTA ===
        final_prompt = f"""
    Eres POLO, asistente conversacional del Parque Industrial Polo 52.

    Información disponible:
    {input_text}

    Historial:
    {chat_history}

    INSTRUCCIONES IMPORTANTES:
    - Responde de forma natural, directa y conversacional.
    - No hagas respuestas muy extensas, se mas directo
    - Si hay más de 8 resultados, di cuántos encontraste y pide más especificidad
    - Si es una lista extensa (mas de 8 items) deci cantidad de resultados pero no expliques cada uno, pedi mas informacion asi filtras resulatdos
    - Si los resultados están vacíos [] o hay error, responde de forma amigable explicando que no encontraste información
    - Si hay 1-8 resultados, muéstralos todos claramente
    - Nunca muestres CUIL ni ID de empresas
    - Nunca uses asteriscos (*) 


    Responde naturalmente:"""

        final_response = model.generate_content(final_prompt)

        return final_response.text, db_results, intent_data.get("corrected_entity")

    except Exception as e:
        return f"Error al procesar el mensaje: {str(e)}", [], None