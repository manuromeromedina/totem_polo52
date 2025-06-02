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
            "1. Analizar la pregunta del usuario y el historial para determinar la intención (por ejemplo, ¿quiere información de una empresa específica, de todas las empresas, servicios, contactos, etc.?). "
            "2. Si la pregunta contiene errores de escritura (por ejemplo, 'Jsoefina' en lugar de 'Josefina'), corrige los nombres o términos aproximados usando ILIKE para buscar coincidencias cercanas en las columnas relevantes (por ejemplo, SELECT nombre FROM tabla WHERE nombre ILIKE '%Jsoefina%'). "
            "3. Si falta información clave (como el nombre de una empresa), responde con un JSON pidiendo aclaración: {'needs_more_info': true, 'question': '¿Puedes especificar de qué empresa quieres información?'}. "
            "4. Si no entiendes la pregunta, responde con un JSON: {'needs_more_info': true, 'question': 'Lo siento, no entiendo tu pregunta. ¿Puedes reformularla o preguntar algo sobre las empresas del Parque Industrial Polo 52?'}. "
            "5. Si la intención es clara, genera una consulta SQL para PostgreSQL basada únicamente en el esquema proporcionado. Usa ILIKE para búsquedas de texto insensibles a mayúsculas/minúsculas. Usa LEFT JOIN para incluir datos opcionales de tablas relacionadas. "
            "6. Responde con un JSON: {'needs_more_info': false, 'sql_query': '...', 'corrected_entity': '...'}. Usa 'corrected_entity' solo si corriges un nombre (por ejemplo, 'corrected_entity': 'Josefina').\n\n"
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

        # Convertir los resultados a una cadena para incluir en el prompt
        db_info = "\n".join([str(result) for result in db_results])

        # Paso 3: Gemini genera la respuesta final con los datos de la base de datos
        final_prompt = (
            "Eres POLO, un asistente del Parque Industrial Polo 52. Tu objetivo es ayudar a los usuarios respondiendo preguntas sobre el parque de manera fluida y profesional. "
            "Se te proporcionarán los datos obtenidos de la base de datos, el historial de la conversación y la pregunta del usuario. "
            "Tu tarea es:\n"
            "1. Analizar los datos devueltos y la pregunta del usuario para generar una respuesta en lenguaje natural. "
            "2. Si los datos están relacionados con una o varias empresas, presenta la información de manera organizada (por ejemplo, 'La empresa [nombre] pertenece al rubro [rubro], tiene [empleados] empleados. Servicios: [servicio]. Contactos: [contacto].'). "
            "3. Si no hay datos relevantes (por ejemplo, campos vacíos o nulos), indica que no se encontró información específica (por ejemplo, 'No se encontraron servicios.' o 'No se encontraron contactos.'). "
            "4. Si no hay datos suficientes para responder, di 'No tengo información suficiente sobre esto. ¿Puedo ayudarte con otra cosa?' y ofrece opciones relevantes. "
            "5. Siempre termina la respuesta ofreciendo más ayuda (por ejemplo, '¿Te gustaría saber más sobre este tema o sobre otro aspecto del Parque Industrial Polo 52?').\n\n"
            "Datos de la base de datos:\n"
            f"{db_info}\n\n"
            "Historial de la conversación:\n"
            + chat_history +
            "\n\nPregunta actual del usuario: " + user_input
        )

        print(f"Prompt enviado a Gemini para respuesta final: {final_prompt}")
        final_response = model.generate_content(final_prompt)
        return final_response.text

    except Exception as e:
        print(f"Error al procesar el mensaje: {str(e)}")
        return f"Error al procesar el mensaje: {str(e)}"