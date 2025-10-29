#app/services.py

import unicodedata
import os
import json
import re
import hashlib
import uuid
import secrets
import string
import smtplib
import io
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from sqlalchemy.sql import text
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from app.config import SECRET_KEY, ALGORITHM
from app import models
from app.models import Empresa, PasswordHistory

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y CONSTANTES
# ═══════════════════════════════════════════════════════════════════

# Cache en memoria para tokens usados (en producción usar Redis)
USED_RESET_TOKENS: Set[str] = set()

# Cargar variables de entorno
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configuración de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configurar API Key de Google Gemini
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

def _init_gemini_model() -> genai.GenerativeModel:
    """
    Intenta inicializar el modelo de Gemini probando varios identificadores.

    Permite configurar uno explícito mediante la variable GEMINI_MODEL.
    Si ese falla (por permisos o disponibilidad), prueba alternativas
    compatibles para no interrumpir el servicio.
    """
    configured = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")
    candidates = [
        configured,
        "gemini-2.5-flash",
        "gemini-2.5-flash-preview-05-20",
        "models/gemini-2.5-flash",
        "models/gemini-2.5-flash-preview-05-20",
        "gemini-2.5-pro",
        "models/gemini-2.5-pro",
        "gemini-1.5-flash",
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "gemini-pro",
        "models/gemini-pro",
    ]

    tried = set()
    last_error = None

    for candidate in candidates:
        if candidate in tried:
            continue
        tried.add(candidate)
        try:
            print(f" Inicializando modelo Gemini: {candidate}")
            return genai.GenerativeModel(
                model_name=candidate,
                generation_config=GenerationConfig(
                    temperature=0.3,
                    top_p=0.9,
                    max_output_tokens=1024,
                    stop_sequences=None,
                    candidate_count=1,
                ),
            )
        except Exception as exc:
            print(f"  No se pudo inicializar {candidate}: {exc}")
            last_error = exc

    raise RuntimeError(
        "No se pudo inicializar ningún modelo de Gemini. "
        "Verifica la variable GEMINI_MODEL o los permisos de tu API key."
    ) from last_error


# Configuración del modelo Gemini (con fallback)
model = _init_gemini_model()

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE SERVICIOS DE VOZ (SOLO GOOGLE CLOUD)
# ═══════════════════════════════════════════════════════════════════

try:
    from google.cloud import speech_v1 as speech
    from google.cloud import texttospeech

    google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if google_credentials_path and os.path.exists(google_credentials_path):
        speech_client = speech.SpeechClient()
        tts_client = texttospeech.TextToSpeechClient()
        VOICE_PROVIDER = "google"
        print(" Google Cloud Speech/TTS configurado")
    else:
        speech_client = None
        tts_client = None
        VOICE_PROVIDER = None
        print(" Credenciales de Google Cloud no encontradas")
except ImportError:
    speech_client = None
    tts_client = None
    VOICE_PROVIDER = None
    print(" google-cloud-speech/texttospeech no instalados")

# ═══════════════════════════════════════════════════════════════════
# UTILIDADES DE AUTENTICACIÓN Y CONTRASEÑAS
# ═══════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """Hashear contraseña usando bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crear token JWT de acceso"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def generate_random_password(length: int = 12) -> str:
    """Generar contraseña aleatoria segura"""
    # Definir los caracteres permitidos
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase  
    digits = string.digits
    special_chars = "!@#$%&*"
    
    # Asegurar que tenga al menos uno de cada tipo
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]
    
    # Completar el resto de la longitud
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # Mezclar la contraseña
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE TOKENS DE RECUPERACIÓN
# ═══════════════════════════════════════════════════════════════════

def create_password_reset_token(email: str, expires_minutes: int = 60) -> str:
    """Crear token de recuperación de contraseña con ID único"""
    now = datetime.utcnow()
    exp = now + timedelta(minutes=expires_minutes)
    
    # Crear ID único para este token específico
    token_id = str(uuid.uuid4())
    
    to_encode = {
        "sub": email, 
        "exp": exp, 
        "type": "password_reset",
        "iat": now,
        "jti": token_id  # JWT ID único para identificar este token específico
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def is_token_already_used(token_id: str) -> bool:
    """Verificar si el token ya fue usado"""
    return token_id in USED_RESET_TOKENS

def mark_token_as_used(token_id: str) -> None:
    """Marcar un token como usado"""
    USED_RESET_TOKENS.add(token_id)
    
    # Limpiar tokens viejos para no llenar la memoria
    if len(USED_RESET_TOKENS) > 1000:  # Límite arbitrario
        USED_RESET_TOKENS.clear()

def verify_password_reset_token(token: str) -> str:
    """Verificar token de recuperación y devolver el email (sin consumir)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verificar que sea un token de reset
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=401, 
                detail="Token de tipo inválido"
            )
        
        email = payload.get("sub")
        token_id = payload.get("jti")
        
        if not email:
            raise HTTPException(
                status_code=401, 
                detail="Token inválido - falta información del usuario"
            )
        
        if not token_id:
            raise HTTPException(
                status_code=401, 
                detail="Token inválido - falta identificador único"
            )
        
        # Verificar si el token ya fue usado
        if is_token_already_used(token_id):
            raise HTTPException(
                status_code=400,
                detail="Este enlace de recuperación ya fue utilizado. Solicita uno nuevo.",
                headers={"X-Error-Type": "used"}
            )
            
        return email
        
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=400, 
            detail="El enlace de recuperación ha expirado. Solicita uno nuevo.",
            headers={"X-Error-Type": "expired"}
        )
    except JWTError as e:
        raise HTTPException(
            status_code=401, 
            detail="Token de recuperación inválido",
            headers={"X-Error-Type": "invalid"}
        )

def consume_password_reset_token(token: str) -> str:
    """Verificar token Y marcarlo como usado en una sola operación"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=401, detail="Token de tipo inválido")
        
        email = payload.get("sub")
        token_id = payload.get("jti")
        
        if not email or not token_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        # Verificar si ya fue usado
        if is_token_already_used(token_id):
            raise HTTPException(
                status_code=400,
                detail="Este enlace de recuperación ya fue utilizado. Solicita uno nuevo.",
                headers={"X-Error-Type": "used"}
            )
        
        # Marcar como usado inmediatamente
        mark_token_as_used(token_id)
        
        return email
        
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=400, 
            detail="El enlace de recuperación ha expirado. Solicita uno nuevo.",
            headers={"X-Error-Type": "expired"}
        )
    except JWTError:
        raise HTTPException(
            status_code=401, 
            detail="Token de recuperación inválido",
            headers={"X-Error-Type": "invalid"}
        )

def check_token_validity(token: str) -> dict:
    """Verificar si un token es válido sin hacer operaciones críticas"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_id = payload.get("jti")
        
        # Verificar si ya fue usado
        if token_id and is_token_already_used(token_id):
            return {
                "valid": False,
                "error": "used",
                "message": "Token ya utilizado"
            }
        
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

def cleanup_used_tokens():
    """Limpiar cache de tokens usados"""
    global USED_RESET_TOKENS
    USED_RESET_TOKENS.clear()
    print("Cache de tokens usados limpiado")

def get_used_tokens_count() -> int:
    """Obtener cantidad de tokens usados en memoria"""
    return len(USED_RESET_TOKENS)

# ═══════════════════════════════════════════════════════════════════
# HISTORIAL DE CONTRASEÑAS
# ═══════════════════════════════════════════════════════════════════

def save_password_to_history(db: Session, user_id: str, password_hash: str) -> None:
    """Guarda una contraseña en el historial del usuario"""
    password_entry = PasswordHistory(
        id_usuario=user_id,
        password_hash=password_hash,
        created_at=date.today()
    )
    db.add(password_entry)
    
    # Mantener solo las últimas 5 contraseñas para no llenar la BD
    old_passwords = (
        db.query(PasswordHistory)
        .filter(PasswordHistory.id_usuario == user_id)
        .order_by(PasswordHistory.created_at.desc())
        .offset(5)
        .all()
    )
    
    for old_pwd in old_passwords:
        db.delete(old_pwd)

def is_password_reused(db: Session, user_id: str, new_password: str) -> bool:
    """Verifica si la nueva contraseña ya fue utilizada anteriormente"""
    # Obtener historial de contraseñas del usuario (últimas 5)
    password_history = (
        db.query(PasswordHistory)
        .filter(PasswordHistory.id_usuario == user_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(5)
        .all()
    )
    
    # Verificar si alguna coincide con la nueva contraseña
    for pwd_entry in password_history:
        if verify_password(new_password, pwd_entry.password_hash):
            return True
    
    # También verificar contra la contraseña actual del usuario
    current_user = db.query(models.Usuario).filter(models.Usuario.id_usuario == user_id).first()
    if current_user and verify_password(new_password, current_user.contrasena):
        return True
    
    return False

def forgot_password_reset_confirm(
    db: Session,
    token: str,
    new_password: str,
    confirm_password: str
) -> dict:
    """Confirmación de reset para contraseña olvidada (sin validar contraseña actual)"""
    try:
        # 1. Verificar que las contraseñas nuevas coincidan
        if new_password != confirm_password:
            raise HTTPException(
                status_code=400,
                detail="Las contraseñas nuevas no coinciden"
            )
        
        # 2. VERIFICAR el token SIN consumir (solo validar)
        email = verify_password_reset_token(token)
        
        # 3. Obtener usuario
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # 4. Verificar que no esté reutilizando contraseña
        if is_password_reused(db, user.id_usuario, new_password):
            # NO consumir el token si hay error de reutilización
            raise HTTPException(
                status_code=400,
                detail="No puedes usar una contraseña que ya hayas utilizado anteriormente. Elige una contraseña diferente."
            )
        
        # 5. AHORA SÍ marcar el token como usado MANUALMENTE
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_id = payload.get("jti")
            if token_id:
                mark_token_as_used(token_id)
        except:
            # Si hay error decodificando, es raro pero continuamos
            pass
        
        # 6. Guardar contraseña actual en historial
        save_password_to_history(db, user.id_usuario, user.contrasena)
        
        # 7. Actualizar contraseña
        user.contrasena = hash_password(new_password)
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "message": "Contraseña restablecida correctamente. Ya puedes iniciar sesión con tu nueva contraseña."
        }
        
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar contraseña: {str(e)}"
        )

def secure_password_reset_confirm(
    db: Session,
    token: str,
    current_password: str,
    new_password: str,
    confirm_password: str
) -> dict:
    """Confirmación segura de reset con validación completa"""
    try:
        # 1. Verificar que las contraseñas nuevas coincidan
        if new_password != confirm_password:
            raise HTTPException(
                status_code=400,
                detail="Las contraseñas nuevas no coinciden"
            )
        
        # 2. VERIFICAR el token SIN consumir (solo validar)
        email = verify_password_reset_token(token)
        
        # 3. Obtener usuario
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # 4. Verificar contraseña actual
        if not verify_password(current_password, user.contrasena):
            raise HTTPException(
                status_code=400,
                detail="La contraseña actual es incorrecta"
            )
        
        # 5. Verificar que no esté reutilizando contraseña
        if is_password_reused(db, user.id_usuario, new_password):
            raise HTTPException(
                status_code=400,
                detail="No puedes usar una contraseña que ya hayas utilizado anteriormente. Elige una contraseña diferente."
            )
        
        # 6. AHORA SÍ marcar el token como usado MANUALMENTE
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_id = payload.get("jti")
            if token_id:
                mark_token_as_used(token_id)
        except:
            # Si hay error decodificando, es raro pero continuamos
            pass
        
        # 7. Guardar contraseña actual en historial
        save_password_to_history(db, user.id_usuario, user.contrasena)
        
        # 8. Actualizar contraseña
        user.contrasena = hash_password(new_password)
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "message": "Contraseña actualizada correctamente. Este enlace ya no es válido."
        }
        
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar contraseña: {str(e)}"
        )

def send_password_change_notification(email: str, nombre: str) -> bool:
    """Envía notificación por email cuando se cambia la contraseña desde la web"""
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("EMAIL_USER")
        smtp_password = os.getenv("EMAIL_PASS")
        
        if not smtp_user or not smtp_password:
            print("Configuración SMTP no encontrada")
            return False
            
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = "Contraseña Cambiada - Polo 52"
        
        # Obtener fecha y hora actual
        fecha_cambio = datetime.now().strftime("%d/%m/%Y a las %H:%M")
        
        # Cuerpo del email
        body = f"""
Hola {nombre},

Te informamos que tu contraseña ha sido cambiada exitosamente el {fecha_cambio}.

DETALLES DEL CAMBIO:
• Cambio realizado desde: Aplicación Web (usuario logueado)
• Fecha y hora: {fecha_cambio}
• IP: [Sistema interno]

Si no realizaste este cambio, contacta inmediatamente con el administrador del sistema.

RECORDATORIOS DE SEGURIDAD:
• Nunca compartas tu contraseña con otras personas
• Usa contraseñas únicas y seguras
• Si sospechas actividad no autorizada, cambia tu contraseña inmediatamente

Saludos,
Administración Polo 52
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Enviar el email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, email, text)
        server.quit()
        
        print(f"Notificación de cambio de contraseña enviada a {email}")
        return True
        
    except Exception as e:
        print(f"Error enviando notificación: {str(e)}")
        return False

# ═══════════════════════════════════════════════════════════════════
# ENVÍO DE EMAILS
# ═══════════════════════════════════════════════════════════════════

def send_welcome_email(email: str, nombre: str, username: str, password: str) -> bool:
    """Envía email de bienvenida con credenciales"""
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("EMAIL_USER")
        smtp_password = os.getenv("EMAIL_PASS")
        
        if not smtp_user or not smtp_password:
            print("Configuración SMTP no encontrada")
            return False
            
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = "Bienvenido al Parque Industrial Polo 52"
        
        # Cuerpo del email
        body = f"""
Hola {nombre},

Se le ha creado una nueva cuenta en "Parque Industrial Polo 52".

Sus credenciales de acceso son:

Nombre de usuario: {username}
Contraseña temporal: {password}

Se le recomienda solicitar el cambio de contraseña cuando acceda por primera vez.

Para comenzar a usar el sistema, ingrese en:
http://localhost:4200/login

Si necesita ayuda, puede contactar con el administrador del sitio.

Saludos,
Administración Polo 52
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Enviar el email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, email, text)
        server.quit()
        
        print(f"Email enviado exitosamente a {email}")
        return True
        
    except Exception as e:
        print(f"Error enviando email: {str(e)}")
        return False


# ═══════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE VOZ - SPEECH TO TEXT
# ═══════════════════════════════════════════════════════════════════

def transcribe_audio_google(audio_content: bytes, language_code: str = "es-ES") -> str:
    """
    Convertir audio a texto usando Google Speech-to-Text
    
    Args:
        audio_content: Bytes del archivo de audio
        language_code: Código de idioma (español por defecto)
    
    Returns:
        Texto transcrito
    """
    try:
        if not speech_client:
            raise HTTPException(
                status_code=503,
                detail="Servicio de transcripción no disponible"
            )
        
        audio = speech.RecognitionAudio(content=audio_content)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=language_code,
            enable_automatic_punctuation=True,
            model="default",
            use_enhanced=True
        )
        
        response = speech_client.recognize(config=config, audio=audio)
        
        if not response.results:
            return ""
        
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
        
        final_transcript = transcript.strip()
        print(f" Transcripción Google: {final_transcript}")
        return final_transcript
        
    except Exception as e:
        print(f" Error en transcripción Google: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al transcribir audio: {str(e)}"
        )

def transcribe_audio(audio_content: bytes, language_code: str = "es-ES") -> str:
    """
    Transcribir audio usando Google Cloud
    """
    if VOICE_PROVIDER == "google" and speech_client:
        return transcribe_audio_google(audio_content, language_code)

    raise HTTPException(
        status_code=503,
        detail="No hay servicio de transcripción configurado. Configura GOOGLE_APPLICATION_CREDENTIALS."
    )

# -------------------------------------------------------------------
# STREAMING (Opcional)
# -------------------------------------------------------------------
# Las siguientes referencias quedan comentadas para habilitar audio
# en streaming cuando se necesite. Requiere crear un cliente de
# streaming (`speech.SpeechClient().streaming_recognize`) y gestionar
# un generador de fragmentos de audio desde el frontend (WebSocket o
# HTTP chunked). Ejemplo orientativo:
#
# from collections import deque
# from google.cloud.speech_v1 import StreamingRecognizeRequest
# 
# class StreamingBuffer:
#     """Buffer simple para combinar frames recibidos desde el cliente."""
#     def __init__(self) -> None:
#         self._frames = deque()
# 
#     def push(self, frame: bytes) -> None:
#         self._frames.append(frame)
# 
#     def flush(self) -> bytes:
#         if not self._frames:
#             return b""
#         joined = b"".join(self._frames)
#         self._frames.clear()
#         return joined
# 
# def generate_streaming_requests(language_code: str = "es-ES"):
#     """Ejemplo de generador para speech.streaming_recognize."""
#     config_request = StreamingRecognizeRequest(
#         streaming_config=speech.StreamingRecognitionConfig(
#             config=speech.RecognitionConfig(
#                 encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
#                 language_code=language_code,
#                 enable_automatic_punctuation=True,
#             ),
#             interim_results=True,
#         )
#     )
#     yield config_request
#     # Los siguientes yield deben enviar frames recibidos en tiempo real:
#     # while True:
#     #     frame = streaming_buffer.flush()
#     #     if frame:
#     #         yield StreamingRecognizeRequest(audio_content=frame)
# 
# def consume_streaming_results(responses):
#     """Procesa resultados parciales y finales."""
#     for response in responses:
#         for result in response.results:
#             if result.is_final:
#                 print("✳️ Final:", result.alternatives[0].transcript)
#             else:
#                 print("🟡 Parcial:", result.alternatives[0].transcript)
#
# ═══════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE VOZ - TEXT TO SPEECH
# ═══════════════════════════════════════════════════════════════════

def text_to_speech_google(text: str, language_code: str = "es-ES", voice_name: str = "es-ES-Neural2-A") -> bytes:
    """
    Convertir texto a voz usando Google Text-to-Speech
    
    Args:
        text: Texto a convertir
        language_code: Código de idioma
        voice_name: Nombre de la voz
    
    Returns:
        Bytes del audio en formato MP3
    """
    try:
        if not tts_client:
            raise HTTPException(
                status_code=503,
                detail="Servicio de síntesis de voz no disponible"
            )
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0,
            effects_profile_id=["headphone-class-device"]
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        print(f" Audio Google generado: {len(response.audio_content)} bytes")
        return response.audio_content
        
    except Exception as e:
        print(f" Error en síntesis Google: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar audio: {str(e)}"
        )

def text_to_speech(text: str, voice_provider: str = None) -> bytes:
    """
    Sintetizar voz usando Google Cloud
    
    Args:
        text: Texto a sintetizar
        voice_provider: Proveedor específico (solo se admite 'google')
    
    Returns:
        Bytes del audio MP3
    """
    if voice_provider and voice_provider != "google":
        raise HTTPException(
            status_code=400,
            detail="Proveedor de voz no soportado. Usa 'google'."
        )

    if VOICE_PROVIDER == "google" and tts_client:
        return text_to_speech_google(text)

    raise HTTPException(
        status_code=503,
        detail="No hay servicio de síntesis de voz configurado. Configura GOOGLE_APPLICATION_CREDENTIALS."
    )

# -------------------------------------------------------------------
# STREAMING TTS (Opcional)
# -------------------------------------------------------------------
# Google Text-to-Speech responde con un único payload. Si se desea
# enviar audio por fragmentos al frontend, se puede dividir el MP3
# en chunks antes de transmitirlo (por ejemplo, via WebSocket):
#
# import math
# 
# def chunk_audio_payload(audio_bytes: bytes, chunk_size: int = 32_768):
#     """Divide el MP3 en fragmentos listos para transmisión iterativa."""
#     total = len(audio_bytes)
#     for index in range(0, total, chunk_size):
#         yield audio_bytes[index:index + chunk_size]
# 
# El cliente podría reproducir cada fragmento a medida que llega
# utilizando la API Web Audio o MediaSource Extensions.

# ═══════════════════════════════════════════════════════════════════
# UTILIDADES DEL CHATBOT CON GEMINI
# ═══════════════════════════════════════════════════════════════════

def normalize_text(text: str) -> str:
    """Normalizar texto eliminando acentos y convirtiendo a minúsculas"""
    normalized = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return normalized.lower().strip()

def execute_sql_query(db: Session, query: str) -> List[Dict]:
    """Ejecutar consulta SQL de forma segura (solo SELECT)"""
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
    """Obtener esquema de la base de datos para el chatbot"""
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
    """Serializar objetos date para JSON"""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

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

        # Prompt para interpretación de la consulta
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

        # Prompt para respuesta natural
        final_prompt = f"""
Eres POLO, asistente conversacional del Parque Industrial Polo 52.

Información disponible:
{input_text}

Historial:
{chat_history}

- INSTRUCCIONES IMPORTANTES: - Solo responde consultas sobre el Parque Industrial Polo 52. Si la consulta es ajena, responde textualmente: "Solo puedo ayudarte con información del Parque Industrial Polo 52." 
- Responde de forma natural, directa y segura, usando un tono informativo. No cierres la respuesta con preguntas ni pidas más detalles. 
- Cuando haya resultados, menciónalos en texto corrido o en una lista corta usando viñetas simples (por ejemplo "- Empresa: dato relevante"). Si hay más de seis coincidencias, indica cuántas hay y describe las seis más representativas. 
- Si no encuentras información, indícalo claramente y ofrece una alternativa relacionada con el parque (por ejemplo, sugerir otro rubro o empresa) sin agregar preguntas. 
- Nunca muestres CUIL, IDs internos ni datos sensibles. 
- Evita cualquier caracter de viñeta distinto a los guiones, especialmente asteriscos (*). 
- Asegúrate de que la respuesta sea apropiada para todo público. 

Responde naturalmente:"""

        final_response = model.generate_content(final_prompt)

        return final_response.text, db_results, intent_data.get("corrected_entity")

    except Exception as e:
        return f"Error al procesar el mensaje: {str(e)}", [], None
    

# ═══════════════════════════════════════════════════════════════════
# CHATBOT CON VOZ - FUNCIÓN INTEGRADA
# ═══════════════════════════════════════════════════════════════════

def get_chat_response_with_audio(
    db: Session, 
    audio_content: bytes = None,
    text_message: str = None,
    history: List[Dict[str, str]] = None
) -> dict:
    """
    Procesar mensaje de voz o texto y devolver respuesta con audio
    
    Args:
        db: Sesión de base de datos
        audio_content: Audio en bytes (opcional)
        text_message: Mensaje de texto (opcional)
        history: Historial de conversación
    
    Returns:
        dict con:
        - text: Respuesta en texto
        - audio_base64: Audio de respuesta en base64
        - db_results: Resultados de la base de datos
        - transcript: Transcripción del audio del usuario (si aplica)
        - corrected_entity: Entidad corregida (si aplica)
    """
    try:
        transcript = None
        
        # 1. Si viene audio, transcribir a texto
        if audio_content:
            print(f" Procesando audio: {len(audio_content)} bytes")
            transcript = transcribe_audio(audio_content)
            
            if not transcript or len(transcript.strip()) == 0:
                error_message = "No pude entender el audio. ¿Podrías repetir más claro?"
                error_audio = text_to_speech(error_message)
                error_audio_base64 = base64.b64encode(error_audio).decode('utf-8')
                
                return {
                    "text": error_message,
                    "audio_base64": error_audio_base64,
                    "db_results": [],
                    "transcript": None,
                    "corrected_entity": None,
                    "error": True
                }
            
            message = transcript
            print(f" Transcripción: {message}")
            
        elif text_message:
            message = text_message
            print(f" Mensaje de texto: {message}")
        else:
            raise HTTPException(
                status_code=400, 
                detail="Se requiere audio o texto"
            )
        
        # 2. Obtener respuesta del chatbot
        print(f" Procesando con Gemini...")
        response_text, db_results, corrected_entity = get_chat_response(
            db, message, history
        )
        
        print(f" Respuesta generada: {response_text[:100]}...")
        
        # 3. Convertir respuesta a audio
        print(f"🔊 Generando audio de respuesta...")
        audio_bytes = text_to_speech(response_text)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        print(f" Audio generado: {len(audio_base64)} caracteres en base64")
        
        return {
            "text": response_text,
            "audio_base64": audio_base64,
            "db_results": db_results,
            "transcript": transcript,
            "corrected_entity": corrected_entity,
            "error": False
        }
        
    except HTTPException as he:
        # Re-lanzar excepciones HTTP
        raise he
    except Exception as e:
        error_msg = f"Error procesando consulta: {str(e)}"
        print(f" {error_msg}")
        
        # Intentar generar respuesta de error con audio
        try:
            error_response = "Disculpa, tuve un problema técnico. ¿Podrías intentar de nuevo?"
            error_audio = text_to_speech(error_response)
            error_audio_base64 = base64.b64encode(error_audio).decode('utf-8')
            
            return {
                "text": error_response,
                "audio_base64": error_audio_base64,
                "db_results": [],
                "transcript": transcript,
                "corrected_entity": None,
                "error": True,
                "error_detail": str(e)
            }
        except:
            # Si falla todo, devolver solo texto
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

# ═══════════════════════════════════════════════════════════════════
# UTILIDADES DE DIAGNÓSTICO Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

def get_voice_services_status() -> dict:
    """
    Obtener estado de los servicios de voz configurados
    
    Returns:
        dict con el estado de cada servicio
    """
    status = {
        "provider": VOICE_PROVIDER,
        "services": {}
    }
    
    # Verificar Google Cloud
    if speech_client and tts_client:
        status["services"]["google_cloud"] = {
            "speech_to_text": " Disponible",
            "text_to_speech": " Disponible"
        }
    else:
        status["services"]["google_cloud"] = {
            "speech_to_text": " No disponible",
            "text_to_speech": " No disponible",
            "note": "Configura GOOGLE_APPLICATION_CREDENTIALS"
        }
    
    return status

def test_voice_pipeline(db: Session, test_text: str = "Hola, soy POLO Bot del Parque Industrial Polo 52") -> dict:
    """
    Probar pipeline completo de voz
    
    Args:
        db: Sesión de base de datos
        test_text: Texto de prueba
    
    Returns:
        dict con resultados de las pruebas
    """
    results = {
        "text_to_speech": None,
        "chat_response": None,
        "errors": []
    }
    
    # Test 1: Text-to-Speech
    try:
        audio_bytes = text_to_speech(test_text)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        results["text_to_speech"] = {
            "status": " OK",
            "audio_size_bytes": len(audio_bytes),
            "audio_base64_length": len(audio_base64)
        }
    except Exception as e:
        results["text_to_speech"] = {
            "status": " ERROR",
            "error": str(e)
        }
        results["errors"].append(f"TTS: {str(e)}")
    
    # Test 2: Chat Response
    try:
        response_text, db_results, _ = get_chat_response(
            db, 
            "¿Qué servicios ofrece el parque?",
            None
        )
        results["chat_response"] = {
            "status": " OK",
            "response_length": len(response_text),
            "db_results_count": len(db_results)
        }
    except Exception as e:
        results["chat_response"] = {
            "status": " ERROR",
            "error": str(e)
        }
        results["errors"].append(f"Chat: {str(e)}")
    
    # Resumen
    results["summary"] = " Todos los tests pasaron" if len(results["errors"]) == 0 else f" {len(results['errors'])} errores encontrados"
    
    return results

# ═══════════════════════════════════════════════════════════════════
# LIMPIEZA Y MANTENIMIENTO
# ═══════════════════════════════════════════════════════════════════

def cleanup_used_tokens():
    """Limpiar cache de tokens usados"""
    global USED_RESET_TOKENS
    USED_RESET_TOKENS.clear()
    print(" Cache de tokens usados limpiado")

def get_used_tokens_count() -> int:
    """Obtener cantidad de tokens usados en memoria"""
    return len(USED_RESET_TOKENS)