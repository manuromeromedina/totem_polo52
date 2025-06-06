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

import json
from datetime import date

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
        # Configurar el modelo
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Normalizar el mensaje del usuario
        user_input = normalize_text(message)
        print(f"Mensaje recibido: {message}")

        # Construir el historial de la conversación
        chat_history = ""
        if history:
            for entry in history:
                if entry.get("user"):
                    chat_history += f"Usuario: {entry['user']}\n"
                if entry.get("assistant"):
                    chat_history += f"Asistente: {entry['assistant']}\n"

        # Obtener la estructura de la base de datos
        db_schema = get_database_schema(db)
        print(f"Esquema de la base de datos: {db_schema}")

        # Paso 1: Gemini analiza la pregunta y genera la consulta SQL
        intent_prompt = (
            "Tu nombre es POLO, un asistente del Parque Industrial Polo 52. Tu objetivo es ayudar a los usuarios respondiendo preguntas sobre las empresas y datos relacionados del parque de manera fluida y natural, tienes que generar una conversacion fluida, como si fueses una persona. "
            "Se te proporcionará el esquema de la base de datos, el historial de la conversación y la pregunta actual del usuario. "
            "Solo podés usar nombres de columnas y tablas que existan explícitamente en el esquema proporcionado."
            "Tu tarea es:\n"
            "1. Analizar la pregunta del usuario y el historial para determinar la intención (por ejemplo, ¿quiere información de una empresa específica, de todas las empresas, servicios, contactos, o relaciones entre ellos?). "
            "2. Diferenciar entre 'servicio' y 'servicio polo':\n"
            "   - 'Servicio' se refiere a servicios generales que no son específicos del parque, como 'agua', 'residuos', 'electricidad', entre otros. Por defecto, asume que servicios como estos deben buscarse en la tabla 'servicio', vinculados a empresas a través de 'empresa_servicio' y 'tipo_servicio'. Solo usa esta tabla a menos que el usuario especifique lo contrario.\n"
            "   - 'Servicio polo' se refiere a servicios específicos que las empresas contratan dentro del Parque Industrial Polo 52, como 'nave', 'container', 'oficina'. Usa la tabla 'servicio_polo' solo si la pregunta menciona explícitamente 'servicio polo' o ejemplos como 'nave', 'container', 'oficina'.\n"
            "3. Si la pregunta contiene errores de escritura, corrige los términos aproximados usando ILIKE para buscar coincidencias cercanas en las columnas relevantes, pero solo en campos de tipo texto.\n"
            "4. Si la pregunta requiere relacionar varias tablas, usa las relaciones definidas en el esquema (como claves foráneas) para generar una consulta SQL con JOIN. Identifica las columnas adecuadas para las uniones basándote en las relaciones del esquema.\n"
            "5. Si falta información clave, responde con un JSON pidiendo aclaración: {'needs_more_info': true, 'question': '¿Puedes especificar de qué empresa o servicio quieres información?'}. "
            "6. Si no entiendes la pregunta, responde con un JSON: {'needs_more_info': true, 'question': 'Lo siento, no entiendo tu pregunta. ¿Puedes reformularla o preguntar algo sobre las empresas del Parque Industrial Polo 52?'}. "
            "7. Si la intención es clara, genera una consulta SQL para PostgreSQL basada únicamente en el esquema proporcionado. Usa ILIKE para búsquedas de texto insensibles a mayúsculas/minúsculas y solo en campos de tipo texto (como 'nombre'). Para campos numéricos (como 'cuil'), usa operadores numéricos como '='. Usa LEFT JOIN for incluir datos opcionales de tablas relacionadas. Si la consulta es para listar todas las empresas, incluye un ORDER BY nombre para ordenar los resultados.\n"
            "8. Responde con un JSON: {'needs_more_info': false, 'sql_query': '...', 'corrected_entity': '...'}. Usa 'corrected_entity' solo si corriges un nombre (por ejemplo, 'corrected_entity': 'Josefina' o 'corrected_entity': 'nave').\n\n"
            "Esquema de la base de datos:\n"
            f"{db_schema}\n\n"
            "Historial de la conversación:\n"
            + chat_history +
            "\n\nPregunta actual del usuario: " + user_input
        )

        print(f"Prompt enviado a Gemini para análisis de intención y generación de SQL: {intent_prompt}")
        intent_response = model.generate_content(intent_prompt)
        intent_response_text = intent_response.text

        # Parsear la respuesta de Gemini como JSON
        try:
            intent_data = json.loads(intent_response_text.strip("```json\n").strip("\n```"))
        except json.JSONDecodeError:
            print(f"Error al parsear la respuesta de Gemini: {intent_response_text}")
            raise HTTPException(status_code=500, detail="Error al procesar la respuesta del modelo.")

        print(f"Respuesta de Gemini: {intent_data}")

        # Paso 2: Si Gemini necesita más información, devolver la pregunta aclaratoria
        if intent_data.get("needs_more_info", False):
            return intent_data["question"], [], intent_data.get("corrected_entity")

        sql_query = intent_data.get("sql_query")
        if not sql_query:
            return "Lo siento, no se pudo generar una consulta válida para tu pregunta. ¿Puedes reformularla?", [], intent_data.get("corrected_entity")

        db_results = execute_sql_query(db, sql_query)

        if db_results and "error" in db_results[0]:
            return db_results[0]["error"], [], intent_data.get("corrected_entity")

        if not db_results:
            entity = intent_data.get("corrected_entity", "desconocida")
            return f"No se encontraron datos para {entity}. ¿Quieres información sobre otra cosa? Por ejemplo, otra empresa o aspecto del Parque Industrial Polo 52.", [], intent_data.get("corrected_entity")

        # Preprocesar resultados
        processed_results = db_results  # Eliminado el filtrado de duplicados

        if processed_results:
            results_text = json.dumps(processed_results, ensure_ascii=False, default=custom_json_serializer)
        else:
            results_text = "[]"

        input_text = f"Pregunta del usuario: {message}\nResultados de la base de datos: {results_text}"
        final_prompt = (
            "Tu nombre es POLO, un asistente conversacional del Parque Industrial Polo 52. "
            "Tu tarea es usar la información proporcionada sobre la pregunta del usuario y los resultados de la base de datos para responder de manera clara, simple y fácil de entender, sin mostrar detalles técnicos de la consulta SQL al usuario final. "
            "Instrucciones:\n"
            "- La información incluye la pregunta del usuario y los resultados de la base de datos como texto. Los resultados son la respuesta directa a la pregunta del usuario y ya han sido procesados para ser relevantes.\n"
            "- Si los resultados de la base de datos son distintos de 'No se encontraron resultados', significa que hay datos válidos para responder. Usa esos datos directamente para responder a la pregunta.\n"
            "- Estructura la respuesta de manera amigable y organizada. Comienza con una salutación ('Hola, soy POLO, tu asistente del Parque Industrial Polo 52.'), presenta la información basada en los resultados (por ejemplo, 'Los tipos de servicio de polo disponibles son: coworking, oficina.'), y termina ofreciendo más ayuda ('¿Te gustaría saber más sobre otro aspecto del Parque Industrial Polo 52?').\n"
            "- Si los resultados de la base de datos son exactamente 'No se encontraron resultados', responde with: 'Hola, soy POLO, tu asistente del Parque Industrial Polo 52. No se encontraron resultados para tu solicitud. ¿Te gustaría saber más?'.\n"
            "- Adapta la respuesta al contexto de la pregunta del usuario (por ejemplo, si menciona 'servicio', enfócate en servicios). Usa el historial de conversación para dar contexto adicional si es necesario.\n"
            f"Información proporcionada:\n{input_text}\n"
            f"Historial de la conversación:\n{chat_history}"
        )

        final_response = model.generate_content(final_prompt)
        final_response_text = final_response.text
        return final_response_text, processed_results, intent_data.get("corrected_entity")

    except Exception as e:
        print(f"Error al procesar el mensaje: {str(e)}")
        return f"Error al procesar el mensaje: {str(e)}", [], None