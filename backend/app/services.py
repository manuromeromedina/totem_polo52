# app/services.py

from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM, SessionLocal
import os
from dotenv import load_dotenv
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.models import Empresa  # Importa el modelo Empresa

# Contexto para bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tiempo de expiración por defecto (minutos)
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    """
    Hashea la contraseña en claro usando bcrypt.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que la contraseña en claro coincida con el hash almacenado.
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Genera un JWT incluyendo los campos de `data` y un 'exp' que vence tras
    ACCESS_TOKEN_EXPIRE_MINUTES (o el expires_delta pasado).
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

# --- Funciones para el chatbot ---

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def get_empresas(db: Session, empresa: str = None):
    try:
        if empresa:
            query = db.query(Empresa).filter(Empresa.nombre.ilike(f"%{empresa}%")).all()
        else:
            query = db.query(Empresa).all()
        
        if query:
            return [f"Empresa: {e.nombre}, Rubro: {e.rubro}, Horario: {e.horario_trabajo}, Cantidad de empleados: {e.cant_empleados}" for e in query]
        return ["No se encontraron empresas."]
    except Exception as e:
        print(f"Error al consultar empresas: {e}")
        return ["Error al consultar la base de datos."]

def get_empresas_por_rubro(db: Session, rubro: str):
    try:
        query = db.query(Empresa).filter(Empresa.rubro.ilike(f"%{rubro}%")).all()
        if query:
            return [f"Empresa: {e.nombre}, Rubro: {e.rubro}, Horario: {e.horario_trabajo}, Cantidad de empleados: {e.cant_empleados}" for e in query]
        return ["No se encontraron empresas para este rubro."]
    except Exception as e:
        print(f"Error al consultar empresas: {e}")
        return ["Error al consultar la base de datos."]

def get_chat_response(db: Session, message: str):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        user_input = message.lower().strip()
        db_info = ""

        print(f"Mensaje recibido: {message}")  # Depuración
        if "rubro" in user_input:
            rubro = user_input.split("rubro")[1].strip() if "rubro" in user_input else "todos"
            empresas = get_empresas_por_rubro(db, rubro)
            db_info = "\n".join(empresas)
            print(f"Empresas por rubro ({rubro}): {empresas}")  # Depuración
        elif "ubicación" in user_input or "dónde" in user_input:
            empresa = user_input.split("ubicación")[0].split()[-1] if "ubicación" in user_input else user_input.split("dónde")[0].split()[-1]
            empresas = get_empresas(db, empresa)
            db_info = "\n".join(empresas)
            print(f"Empresas por ubicación/dónde ({empresa}): {empresas}")  # Depuración
        elif "horario" in user_input:
            empresa = user_input.split("horario")[0].split()[-1] if "horario" in user_input else "Polo 52"
            empresas = get_empresas(db, empresa)
            db_info = "\n".join(empresas)
            print(f"Empresas por horario ({empresa}): {empresas}")  # Depuración
        elif "contacto" in user_input:
            empresa = user_input.split("contacto")[0].split()[-1] if "contacto" in user_input else "Polo 52"
            empresas = get_empresas(db, empresa)
            db_info = "\n".join(empresas)
            print(f"Empresas por contacto ({empresa}): {empresas}")  # Depuración
        elif "empresas" in user_input:
            empresas = get_empresas(db)
            db_info = "\n".join(empresas)
            print(f"Todas las empresas: {empresas}")  # Depuración
        else:
            db_info = "No se identificó un tipo de consulta específico."
            print("No se identificó un tipo de consulta específico")  # Depuración

        prompt = (
            "Eres POLO, un asistente del Parque Industrial Polo 52. Tu objetivo es ayudar a los usuarios respondiendo preguntas sobre el parque, "
            "usando la siguiente información de la base de datos: \n{db_info}\n"
            "Responde de forma clara y profesional en español. Si no tienes suficiente información, di que no tienes datos específicos y ofrece ayuda con otra pregunta. "
            f"Pregunta del usuario: {message}"
        ).format(db_info=db_info)

        print(f"Prompt enviado a Gemini: {prompt}")  # Depuración
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt)
        return response.text

    except Exception as e:
        print(f"Error al procesar el mensaje: {str(e)}")
        return f"Error al procesar el mensaje: {str(e)}"