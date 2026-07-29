# app/services/auth_service.py
import secrets
import string
import uuid
from datetime import date, datetime, timedelta
from typing import Optional, Set

from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import ALGORITHM, SECRET_KEY
from app import models
from app.models import PasswordHistory

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Cache en memoria para tokens usados (en producción usar Redis)
USED_RESET_TOKENS: Set[str] = set()

# ═══════════════════════════════════════════════════════════════════
# CONTRASEÑAS Y TOKENS DE ACCESO
# ═══════════════════════════════════════════════════════════════════


def hash_password(password: str) -> str:
    """Hashear contraseña usando bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear token JWT de acceso"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_random_password(length: int = 12) -> str:
    """Generar contraseña aleatoria segura"""
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%&*"

    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars),
    ]

    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    secrets.SystemRandom().shuffle(password)
    return "".join(password)


# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE TOKENS DE RECUPERACIÓN
# ═══════════════════════════════════════════════════════════════════


def create_password_reset_token(email: str, expires_minutes: int = 60) -> str:
    """Crear token de recuperación de contraseña con ID único"""
    now = datetime.utcnow()
    exp = now + timedelta(minutes=expires_minutes)
    token_id = str(uuid.uuid4())

    to_encode = {
        "sub": email,
        "exp": exp,
        "type": "password_reset",
        "iat": now,
        "jti": token_id,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def is_token_already_used(token_id: str) -> bool:
    """Verificar si el token ya fue usado"""
    return token_id in USED_RESET_TOKENS


def mark_token_as_used(token_id: str) -> None:
    """Marcar un token como usado"""
    USED_RESET_TOKENS.add(token_id)
    if len(USED_RESET_TOKENS) > 1000:  # Límite arbitrario para no llenar la memoria
        USED_RESET_TOKENS.clear()


def verify_password_reset_token(token: str) -> str:
    """Verificar token de recuperación y devolver el email (sin consumir)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=401, detail="Token de tipo inválido")

        email = payload.get("sub")
        token_id = payload.get("jti")

        if not email:
            raise HTTPException(status_code=401, detail="Token inválido - falta información del usuario")
        if not token_id:
            raise HTTPException(status_code=401, detail="Token inválido - falta identificador único")

        if is_token_already_used(token_id):
            raise HTTPException(
                status_code=400,
                detail="Este enlace de recuperación ya fue utilizado. Solicita uno nuevo.",
                headers={"X-Error-Type": "used"},
            )

        return email

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=400,
            detail="El enlace de recuperación ha expirado. Solicita uno nuevo.",
            headers={"X-Error-Type": "expired"},
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token de recuperación inválido",
            headers={"X-Error-Type": "invalid"},
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

        if is_token_already_used(token_id):
            raise HTTPException(
                status_code=400,
                detail="Este enlace de recuperación ya fue utilizado. Solicita uno nuevo.",
                headers={"X-Error-Type": "used"},
            )

        mark_token_as_used(token_id)
        return email

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=400,
            detail="El enlace de recuperación ha expirado. Solicita uno nuevo.",
            headers={"X-Error-Type": "expired"},
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token de recuperación inválido",
            headers={"X-Error-Type": "invalid"},
        )


def check_token_validity(token: str) -> dict:
    """Verificar si un token es válido sin hacer operaciones críticas"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_id = payload.get("jti")

        if token_id and is_token_already_used(token_id):
            return {"valid": False, "error": "used", "message": "Token ya utilizado"}

        return {
            "valid": True,
            "email": payload.get("sub"),
            "expires_at": payload.get("exp"),
            "type": payload.get("type"),
        }
    except ExpiredSignatureError:
        return {"valid": False, "error": "expired", "message": "Token expirado"}
    except JWTError:
        return {"valid": False, "error": "invalid", "message": "Token inválido"}


def cleanup_used_tokens() -> None:
    """Limpiar cache de tokens usados"""
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
    db.add(PasswordHistory(id_usuario=user_id, password_hash=password_hash, created_at=date.today()))

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
    password_history = (
        db.query(PasswordHistory)
        .filter(PasswordHistory.id_usuario == user_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(5)
        .all()
    )
    for pwd_entry in password_history:
        if verify_password(new_password, pwd_entry.password_hash):
            return True

    current_user = db.query(models.Usuario).filter(models.Usuario.id_usuario == user_id).first()
    if current_user and verify_password(new_password, current_user.contrasena):
        return True

    return False


# ═══════════════════════════════════════════════════════════════════
# CONFIRMACIÓN DE RESET DE CONTRASEÑA
# ═══════════════════════════════════════════════════════════════════


def _finalize_password_reset(
    db: Session,
    token: str,
    new_password: str,
    confirm_password: str,
    success_message: str,
    current_password: Optional[str] = None,
) -> dict:
    """
    Lógica común a forgot_password_reset_confirm y secure_password_reset_confirm:
    valida, marca el token como usado y actualiza la contraseña. La única
    diferencia entre ambos flujos es si se exige la contraseña actual.
    """
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Las contraseñas nuevas no coinciden")

    email = verify_password_reset_token(token)

    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if current_password is not None and not verify_password(current_password, user.contrasena):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")

    if is_password_reused(db, user.id_usuario, new_password):
        raise HTTPException(
            status_code=400,
            detail="No puedes usar una contraseña que ya hayas utilizado anteriormente. Elige una contraseña diferente.",
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_id = payload.get("jti")
        if token_id:
            mark_token_as_used(token_id)
    except JWTError:
        pass  # Si el token ya no decodifica en este punto, seguimos igual

    save_password_to_history(db, user.id_usuario, user.contrasena)
    user.contrasena = hash_password(new_password)
    db.commit()
    db.refresh(user)

    return {"success": True, "message": success_message}


def forgot_password_reset_confirm(db: Session, token: str, new_password: str, confirm_password: str) -> dict:
    """Confirmación de reset para contraseña olvidada (sin validar contraseña actual)"""
    try:
        return _finalize_password_reset(
            db,
            token,
            new_password,
            confirm_password,
            success_message="Contraseña restablecida correctamente. Ya puedes iniciar sesión con tu nueva contraseña.",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno al actualizar contraseña: {str(e)}")


def secure_password_reset_confirm(
    db: Session,
    token: str,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> dict:
    """Confirmación segura de reset con validación completa (requiere contraseña actual)"""
    try:
        return _finalize_password_reset(
            db,
            token,
            new_password,
            confirm_password,
            success_message="Contraseña actualizada correctamente. Este enlace ya no es válido.",
            current_password=current_password,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno al actualizar contraseña: {str(e)}")
