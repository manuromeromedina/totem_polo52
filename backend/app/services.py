# app/services.py
import unicodedata
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM
import os
from dotenv import load_dotenv
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.models import Empresa
from fastapi import HTTPException
from typing import List, Dict, Optional
from sqlalchemy import inspect
from sqlalchemy.sql import text
import json
import re

load_dotenv()

# Configurar Gemini con la clave de API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("No se encontró GOOGLE_API_KEY. Asegúrate de definirla en el archivo .env.")
genai.configure(api_key=api_key)




# Contexto para bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tiempo de expiración por defecto (minutos)
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
            # Añadir relaciones (claves foráneas)
            foreign_keys = inspector.get_foreign_keys(table_name)
            for fk in foreign_keys:
                schema += f"  Relación: '{table_name}.{fk['constrained_columns'][0]}' -> '{fk['referred_table']}.{fk['referred_columns'][0]}'\n"
    return schema






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
            "Eres POLO, un asistente del Parque Industrial Polo 52. Tu objetivo es ayudar a los usuarios respondiendo preguntas sobre las empresas y datos relacionados del parque de manera fluida y natural. "
            "Se te proporcionará el esquema de la base de datos, el historial de la conversación y la pregunta actual del usuario. "
            "Tu tarea es:\n"
            "1. Analizar la pregunta del usuario y el historial para determinar la intención (por ejemplo, ¿quiere información de una empresa específica, de todas las empresas, servicios, contactos, o relaciones entre ellos?). "
            "2. Si la pregunta contiene errores de escritura (por ejemplo, 'cuqles' en lugar de 'cuáles', o 'Jsoefina' en lugar de 'Josefina'), corrige los términos aproximados usando ILIKE para buscar coincidencias cercanas en las columnas relevantes (por ejemplo, SELECT nombre FROM tabla WHERE nombre ILIKE '%Jsoefina%'). "
            "3. Si la pregunta requiere relacionar varias tablas (por ejemplo, 'qué empresas tienen el servicio de polo \"nave\"'), usa las relaciones definidas en el esquema (como claves foráneas) para generar una consulta SQL con JOIN. Por ejemplo, si 'servicio_polo' está relacionado con 'empresa' a través de 'cuil', genera una consulta como: SELECT e.nombre AS empresa_nombre FROM empresa e JOIN servicio_polo sp ON e.cuil = sp.cuil WHERE sp.nombre ILIKE '%nave%'. "
            "4. Si falta información clave (como el nombre de una empresa o el tipo de servicio), responde con un JSON pidiendo aclaración: {'needs_more_info': true, 'question': '¿Puedes especificar de qué empresa o servicio quieres información?'}. "
            "5. Si no entiendes la pregunta, responde con un JSON: {'needs_more_info': true, 'question': 'Lo siento, no entiendo tu pregunta. ¿Puedes reformularla o preguntar algo sobre las empresas del Parque Industrial Polo 52?'}. "
            "6. Si la intención es clara, genera una consulta SQL para PostgreSQL basada únicamente en el esquema proporcionado. Usa ILIKE para búsquedas de texto insensibles a mayúsculas/minúsculas. Usa LEFT JOIN para incluir datos opcionales de tablas relacionadas. "
            "7. Responde con un JSON: {'needs_more_info': false, 'sql_query': '...', 'corrected_entity': '...'}. Usa 'corrected_entity' solo si corriges un nombre (por ejemplo, 'corrected_entity': 'Josefina' o 'corrected_entity': 'nave').\n\n"
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
            return intent_data["question"]

        # Si la intención es clara, ejecutar la consulta SQL
        sql_query = intent_data.get("sql_query")
        if not sql_query:
            return "Lo siento, no se pudo generar una consulta válida para tu pregunta. ¿Puedes reformularla?"

        # Ejecutar la consulta SQL generada por Gemini
        db_results = execute_sql_query(db, sql_query)
        print(f"Resultados de la consulta SQL: {db_results}")

        # Manejar errores en la consulta
        if db_results and "error" in db_results[0]:
            return db_results[0]["error"]

        # Si no hay resultados, devolver un mensaje genérico
        if not db_results:
            entity = intent_data.get("corrected_entity", "desconocida")
            return f"No se encontraron datos para {entity}. ¿Quieres información sobre otra cosa? Por ejemplo, otra empresa o aspecto del Parque Industrial Polo 52."

        # Convertir los resultados a un formato JSON-like más claro
        db_info = json.dumps(db_results, ensure_ascii=False)

        # Depuración: Imprimir el formato exacto de db_info
        print(f"Datos enviados a Gemini (db_info): {db_info}")

        ## Paso 3: Gemini genera la respuesta final con los datos de la base de datos
        final_prompt = (
            "Eres POLO, un asistente del Parque Industrial Polo 52. Tu objetivo es ayudar a los usuarios respondiendo preguntas sobre el parque de manera fluida y profesional.\n"
            "Se te proporcionarán los datos obtenidos de la base de datos en formato JSON, el historial de la conversación y la pregunta del usuario.\n"
            "Tu tarea es:\n"
            "1. Analizar los datos devueltos (en formato JSON), la pregunta del usuario y el historial para generar una respuesta en lenguaje natural que sea relevante y útil.\n"
            "2. Usa los datos devueltos tal como están, incluso si provienen de una consulta que relaciona múltiples tablas (como JOIN). Si los datos incluyen nombres de empresas, servicios, contactos u otros elementos, preséntalos de manera organizada y relacionados con la pregunta (por ejemplo, para '[{{\"nombre\": \"Josefina\"}}]', responde 'Las empresas con este servicio son: Josefina').\n"
            "3. Si el array JSON no está vacío (no es []), considera que contiene datos válidos y relevantes, y úsalos en la respuesta adaptándolos al contexto de la pregunta, incluso si solo incluyen un campo como 'nombre'. Esto es obligatorio, sin excepciones.\n"
            "4. Si el array JSON está completamente vacío (por ejemplo, []), responde con 'No se encontraron datos relacionados con tu solicitud.'\n"
            "5. Adapta la respuesta al contexto de la pregunta: si pregunta por empresas con un servicio, lista las empresas; si pregunta por servicios disponibles, lista los servicios, etc.\n"
            "6. Siempre termina la respuesta ofreciendo más ayuda (por ejemplo, '¿Te gustaría saber más sobre este tema o sobre otro aspecto del Parque Industrial Polo 52?').\n"
            "Datos de la base de datos (en formato JSON):\n"
            f"{db_info}\n"
            "Historial de la conversación:\n"
            f"{chat_history}\n"
            "Pregunta actual del usuario:\n"
            f"{user_input}"
        )

        
        print(f"Prompt enviado a Gemini para respuesta final: {final_prompt}")
        final_response = model.generate_content(final_prompt)
        return final_response.text

    except Exception as e:
        print(f"Error al procesar el mensaje: {str(e)}")
        return f"Error al procesar el mensaje: {str(e)}"
