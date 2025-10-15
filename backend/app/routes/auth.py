#auth.py
from fastapi import Depends, HTTPException, APIRouter, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from jose import JWTError, jwt
from datetime import date, datetime, timedelta
from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app import models, schemas, services
from app.models import Usuario
from app.schemas import PasswordResetRequest, PasswordResetConfirm, PasswordResetConfirmSecure, ChangePasswordDirect, ForgotPasswordReset
from email.mime.text import MIMEText
import smtplib
from app.config import settings
from app.services import (
    secure_password_reset_confirm, 
    forgot_password_reset_confirm,
    is_password_reused, 
    save_password_to_history,
    hash_password,
    verify_password_reset_token,
    consume_password_reset_token,
    create_password_reset_token
)

router = APIRouter()

# OAuth2PasswordBearer para manejar el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y UTILIDADES
# ═══════════════════════════════════════════════════════════════════

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.Usuario:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nombre = payload.get("sub")
        if not nombre:
            raise HTTPException(401, "Token inválido")

        user = (
            db.query(models.Usuario)
            .filter(models.Usuario.nombre == nombre)
            .first()
        )
        if not user:
            raise HTTPException(401, "Usuario no encontrado")

        # Usuario deshabilitado
        if not user.estado:
            raise HTTPException(
                status_code=403,
                detail="Su cuenta ha sido deshabilitada. Contacte con el administrador."
            )

        # Empresa desactivada
        if not user.empresa or not user.empresa.estado:
            raise HTTPException(
                status_code=403,
                detail="La empresa asociada está desactivada."
            )

        return user
    except JWTError:
        raise HTTPException(401, "Token inválido")


# Función para obtener usuario desde cookie de "recordarme"
def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> models.Usuario:
    """
    Obtiene el usuario actual desde token Bearer o cookie de "recordarme"
    Usado para endpoints que pueden funcionar con o sin autenticación
    """
    # 1) Intentar con Authorization: Bearer
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            nombre = payload.get("sub")
            if nombre:
                user = db.query(models.Usuario).filter(models.Usuario.nombre == nombre).first()
                if user and user.estado and user.empresa and user.empresa.estado:
                    return user
        except JWTError:
            pass  # ignorar y seguir a cookie

    # 2) Intentar con cookie remember_token
    remember_token = request.cookies.get("remember_token")
    if remember_token:
        try:
            payload = jwt.decode(remember_token, SECRET_KEY, algorithms=[ALGORITHM])
            nombre = payload.get("sub")
            token_type = payload.get("type")
            if nombre and token_type == "remember":
                user = db.query(models.Usuario).filter(models.Usuario.nombre == nombre).first()
                if user and user.estado and user.empresa and user.empresa.estado:
                    return user
        except JWTError:
            pass

    # 3) Si nada funcionó, no hay usuario válido
    return None


# ═══════════════════════════════════════════════════════════════════
# >>> AGREGADO: Helpers de email para cambio de contraseña (éxito / fallo)
# Reutiliza Gmail SMTP como en /forgot-password
def _send_change_password_success_email(to_email: str, nombre: str):
    cuerpo = f"""
Hola {nombre},

Confirmamos que tu contraseña fue actualizada correctamente.
Si no fuiste vos, por favor contactá al soporte de inmediato.

Saludos,
Administración Polo 52
""".strip()

    msg = MIMEText(cuerpo)
    msg["Subject"] = "Polo 52 - Tu contraseña fue actualizada"
    msg["From"] = settings.EMAIL_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.send_message(msg)
    except Exception:
        # No interrumpir el flujo por error de email
        pass


def _send_change_password_failure_email(to_email: str, nombre: str, reason: str):
    cuerpo = f"""
Hola {nombre},

Se intentó actualizar tu contraseña pero ocurrió un problema:
- Detalle: {reason}

Por favor, intentá nuevamente. Si el problema persiste, contactá soporte.

Saludos,
Administración Polo 52
""".strip()

    msg = MIMEText(cuerpo)
    msg["Subject"] = "Polo 52 - No pudimos actualizar tu contraseña"
    msg["From"] = settings.EMAIL_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.send_message(msg)
    except Exception:
        # No interrumpir el flujo por error de email
        pass
# <<< AGREGADO

# ═══════════════════════════════════════════════════════════════════
# >>> AGREGADO: Cooldown por intentos fallidos en cambio de contraseña
_MAX_FAILS_CHANGE_PW = 3          # intentos fallidos permitidos antes del bloqueo
_COOLDOWN_SECONDS_CHANGE_PW = 60  # segundos de espera al alcanzar el límite

# Estructura en memoria: { user_id: {"fails": int, "lock_until": datetime|None} }
_change_pw_attempts = {}

def _is_change_pw_locked(user_id: int):
    info = _change_pw_attempts.get(user_id)
    if not info:
        return False, 0
    lock_until = info.get("lock_until")
    if lock_until and datetime.utcnow() < lock_until:
        remaining = int((lock_until - datetime.utcnow()).total_seconds())
        return True, max(0, remaining)
    return False, 0

def _register_change_pw_failure(user_id: int):
    info = _change_pw_attempts.get(user_id, {"fails": 0, "lock_until": None})
    info["fails"] = info.get("fails", 0) + 1
    if info["fails"] >= _MAX_FAILS_CHANGE_PW:
        info["lock_until"] = datetime.utcnow() + timedelta(seconds=_COOLDOWN_SECONDS_CHANGE_PW)
        info["fails"] = 0  # opcional: resetea contador al iniciar cooldown
    _change_pw_attempts[user_id] = info
    return info

def _reset_change_pw_attempts(user_id: int):
    if user_id in _change_pw_attempts:
        _change_pw_attempts.pop(user_id, None)
# <<< AGREGADO

# ═══════════════════════════════════════════════════════════════════
# VALIDACIÓN DE ROLES
# ═══════════════════════════════════════════════════════════════════

def require_admin_polo(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Usuario:
    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.roles))
        .filter(Usuario.id_usuario == current_user.id_usuario)
        .first()
    )
    if not any(r.tipo_rol == "admin_polo" for r in user.roles):
        raise HTTPException(403, "Se requiere rol admin_polo")
    return user

def require_empresa_role(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Usuario:
    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.roles))
        .filter(Usuario.id_usuario == current_user.id_usuario)
        .first()
    )
    if not any(r.tipo_rol == "admin_empresa" for r in user.roles):
        raise HTTPException(403, "Se requiere rol admin_empresa")
    return user

def require_public_role(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Usuario:
    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.roles))
        .filter(Usuario.id_usuario == current_user.id_usuario)
        .first()
    )
    if not any(r.tipo_rol == "publico" for r in user.roles):
        raise HTTPException(403, "Se requiere rol 'publico'")
    return current_user

# ═══════════════════════════════════════════════════════════════════
# RUTAS DE AUTENTICACIÓN BÁSICA
# ═══════════════════════════════════════════════════════════════════

@router.post("/register", tags=["auth"])
def register(dto: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Nombre ya existe")
    new = models.Usuario(
        nombre=dto.nombre,
        email=dto.email,
        contrasena=services.hash_password(dto.password),
        estado=True,
        fecha_registro=date.today(),
        cuil=dto.cuil,
    )
    db.add(new)
    db.commit()
    return {"message": "Usuario creado"}

@router.post("/login", response_model=schemas.Token, tags=["auth"])
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    remember_me: bool = False
):
    user = (
        db.query(models.Usuario)
        .filter(
            or_(models.Usuario.nombre == form_data.username,
                models.Usuario.email == form_data.username)
        )
        .first()
    )

    if not user or not services.verify_password(form_data.password, user.contrasena):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Usuario deshabilitado
    if not user.estado:
        raise HTTPException(
            status_code=403,
            detail="Su cuenta ha sido deshabilitada. Contacte con el administrador para más información."
        )

    # Empresa desactivada
    if not user.empresa or not user.empresa.estado:
        raise HTTPException(
            status_code=403,
            detail="La empresa asociada está desactivada."
        )

    # Roles
    roles = (
        db.query(models.Rol.tipo_rol)
        .join(models.RolUsuario, models.Rol.id_rol == models.RolUsuario.id_rol)
        .filter(models.RolUsuario.id_usuario == user.id_usuario)
        .all()
    )
    rol = roles[0][0] if roles else "usuario"

    # Access token
    access_token = services.create_access_token(data={"sub": user.nombre})

    # Cookie remember opcional
    if remember_me:
        remember_data = {
            "sub": user.nombre,
            "type": "remember",
            "exp": datetime.utcnow() + timedelta(days=30)
        }
        remember_token = jwt.encode(remember_data, SECRET_KEY, algorithm=ALGORITHM)
        response.set_cookie(
            key="remember_token",
            value=remember_token,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            secure=False,   # True en prod con HTTPS
            samesite="lax"
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tipo_rol": rol,
        "remember_me": remember_me
    }


@router.post("/logout", tags=["auth"], summary="Cerrar sesión")
def logout(
    response: Response,
    current_user: models.Usuario = Depends(get_current_user)
):
    # Eliminar cookie de "recordarme" si existe
    response.delete_cookie(
        key="remember_token",
        httponly=True,
        secure=False,  # Cambiar a True en producción
        samesite="lax"
    )
    return {"message": "Sesión cerrada correctamente"}

# Nuevo endpoint para verificar si hay sesión activa desde cookie
@router.get("/check-remember", tags=["auth"])
def check_remember_session(
    request: Request,
    db: Session = Depends(get_db)
):
    """Verifica si existe una sesión válida desde cookie de 'recordarme'"""
    user = get_current_user_optional(request, db)
    
    if user:
        # Obtener roles del usuario
        roles = (
            db.query(models.Rol.tipo_rol)
            .join(models.RolUsuario, models.Rol.id_rol == models.RolUsuario.id_rol)
            .filter(models.RolUsuario.id_usuario == user.id_usuario)
            .all()
        )
        rol = roles[0][0] if roles else "usuario"
        
        # Crear nuevo access token para la sesión
        access_token = services.create_access_token(data={"sub": user.nombre})
        
        return {
            "logged_in": True,
            "user": {
                "nombre": user.nombre,
                "email": user.email,
                "tipo_rol": rol
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    return {"logged_in": False}

# ═══════════════════════════════════════════════════════════════════
# CAMBIO DE CONTRASEÑA DIRECTO (USUARIO LOGUEADO)
# ═══════════════════════════════════════════════════════════════════

@router.post("/change-password-direct", tags=["auth"])
def change_password_direct(
    dto: schemas.ChangePasswordDirect,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cambio directo de contraseña (requiere estar logueado)
    """

    # >>> AGREGADO: bloquear si está en cooldown por demasiados intentos
    locked, wait_sec = _is_change_pw_locked(current_user.id_usuario)
    if locked:
        return {
            "success": False,
            "error": f"Demasiados intentos fallidos. Esperá {wait_sec} segundos para reintentar.",
            "cooldown_seconds": wait_sec,
            "locked": True
        }
    # <<< AGREGADO

    try:
        # 1. Verificar contraseña actual
        if not services.verify_password(dto.current_password, current_user.contrasena):
            raise HTTPException(
                status_code=400,
                detail="La contraseña actual es incorrecta"
            )
        
        # 2. Verificar que las contraseñas nuevas coincidan
        if dto.new_password != dto.confirm_password:
            raise HTTPException(
                status_code=400,
                detail="Las contraseñas nuevas no coinciden"
            )
        
        # 3. Verificar que no esté reutilizando contraseña
        if services.is_password_reused(db, current_user.id_usuario, dto.new_password):
            raise HTTPException(
                status_code=400,
                detail="No puedes usar una contraseña que ya hayas utilizado anteriormente"
            )
        
        # 4. Guardar contraseña actual en historial
        services.save_password_to_history(db, current_user.id_usuario, current_user.contrasena)
        
        # 5. Actualizar contraseña
        current_user.contrasena = services.hash_password(dto.new_password)
        db.commit()
        db.refresh(current_user)

        # >>> AGREGADO: resetear intentos en éxito + enviar email de éxito
        _reset_change_pw_attempts(current_user.id_usuario)
        try:
            _send_change_password_success_email(
                to_email=current_user.email,
                nombre=current_user.nombre
            )
        except Exception:
            pass
        # <<< AGREGADO
        
        return {
            "success": True,
            "message": "Contraseña actualizada correctamente"
        }
        
    except HTTPException as e:
        db.rollback()

        # >>> AGREGADO: registrar intento fallido + email de fallo
        _register_change_pw_failure(current_user.id_usuario)
        locked, wait_sec = _is_change_pw_locked(current_user.id_usuario)
        try:
            _send_change_password_failure_email(
                to_email=current_user.email,
                nombre=current_user.nombre,
                reason=e.detail
            )
        except Exception:
            pass
        # <<< AGREGADO

        return {
            "success": False,
            "error": e.detail,
            "locked": locked,
            "cooldown_seconds": wait_sec,
            "wrong_current": "contraseña actual" in e.detail.lower(),
            "password_reused": "ya hayas utilizado" in e.detail.lower(),
            "passwords_mismatch": "no coinciden" in e.detail.lower()
        }

    except Exception as e:
        db.rollback()

        # >>> AGREGADO: registrar intento fallido + email de fallo genérico
        _register_change_pw_failure(current_user.id_usuario)
        locked, wait_sec = _is_change_pw_locked(current_user.id_usuario)
        try:
            _send_change_password_failure_email(
                to_email=current_user.email,
                nombre=current_user.nombre,
                reason="Error interno al actualizar la contraseña"
            )
        except Exception:
            pass
        # <<< AGREGADO

        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar contraseña: {str(e)}"
        )

# ═══════════════════════════════════════════════════════════════════
# RECUPERACIÓN DE CONTRASEÑA VIA EMAIL (USUARIO NO LOGUEADO)
# ═══════════════════════════════════════════════════════════════════

@router.post("/forgot-password", tags=["auth"])
def forgot_password(dto: PasswordResetRequest, db: Session = Depends(get_db)):
    """Solicitar reset de contraseña via email (para usuarios no logueados)"""
    user = db.query(models.Usuario).filter(models.Usuario.email == dto.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email no registrado")
    
    # VALIDACIÓN: No permitir reset de contraseña para usuarios inhabilitados
    if not user.estado:
        raise HTTPException(
            status_code=403, 
            detail="No se puede restablecer la contraseña de una cuenta deshabilitada. "
                   "Contacte con el administrador."
        )
    
    RESET_TOKEN_EXPIRE_MINUTES = 60  # 1 hora
    
    token = services.create_password_reset_token(
        user.email, 
        expires_minutes=RESET_TOKEN_EXPIRE_MINUTES
    )
    
    reset_link = f"http://localhost:4200/reset-password?token={token}"
    
    # Email con instrucciones claras
    email_body = f"""
Hola {user.nombre},

Has solicitado restablecer tu contraseña en el sistema del Parque Industrial Polo 52.

Para proceder con el cambio, haz clic en el siguiente enlace:
{reset_link}

INSTRUCCIONES IMPORTANTES:
• Deberás ingresar una nueva contraseña dos veces para confirmar
• No podrás usar contraseñas que hayas utilizado anteriormente
• Este enlace expirará en 1 hora por seguridad
• Solo se puede usar una vez

REQUISITOS PARA LA NUEVA CONTRASEÑA:
• Mínimo 8 caracteres
• Al menos una letra mayúscula
• Al menos una letra minúscula  
• Al menos un número

Si no solicitaste este cambio, puedes ignorar este email de forma segura.

Saludos,
Administración Polo 52
    """
    
    msg = MIMEText(email_body)
    msg["Subject"] = "Recuperar Contraseña - Polo 52"
    msg["From"] = settings.EMAIL_USER
    msg["To"] = dto.email
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando email: {str(e)}")
    
    return {
        "message": "Se ha enviado un email con instrucciones para restablecer tu contraseña",
        "expires_in_minutes": RESET_TOKEN_EXPIRE_MINUTES,
        "note": "Revisa tu bandeja de entrada y sigue las instrucciones del email"
    }

@router.post("/password-reset/verify-token", tags=["auth"])
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """Verificar si un token de reset es válido sin hacer cambios"""
    try:
        email = services.verify_password_reset_token(token)  # Solo verifica, NO consume
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # VALIDACIÓN: Verificar que el usuario siga habilitado
        if not user.estado:
            raise HTTPException(
                status_code=403, 
                detail="Este enlace no es válido porque la cuenta ha sido deshabilitada. "
                       "Contacte con el administrador."
            )
            
        return {
            "valid": True,
            "message": "Token válido",
            "email": email,
            "user_name": user.nombre
        }
        
    except HTTPException as e:
        return {
            "valid": False,
            "error": e.detail,
            "expired": "expirado" in e.detail.lower(),
            "used": "utilizado" in e.detail.lower(),
            "disabled": "deshabilitada" in e.detail.lower()
        }

@router.post("/forgot-password/confirm", tags=["auth"])
def forgot_password_confirm(
    dto: schemas.ForgotPasswordReset,
    db: Session = Depends(get_db)
):
    """Confirmación de reset para contraseña olvidada (sin contraseña actual)"""
    try:
        # Verificar token y obtener usuario antes de procesar
        email = services.verify_password_reset_token(dto.token)
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # VALIDACIÓN: Verificar que el usuario esté habilitado
        if not user.estado:
            raise HTTPException(
                status_code=403, 
                detail="No se puede restablecer la contraseña de una cuenta deshabilitada. "
                       "Contacte con el administrador."
            )
        
        result = services.forgot_password_reset_confirm(
            db=db,
            token=dto.token,
            new_password=dto.new_password,
            confirm_password=dto.confirm_password
        )
        return result
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail,
            "status_code": e.status_code,
            "expired": e.status_code == 400 and "expirado" in e.detail.lower(),
            "used": e.status_code == 400 and "utilizado" in e.detail.lower(),
            "disabled": e.status_code == 403 and "deshabilitada" in e.detail.lower(),
            "password_reused": "ya hayas utilizado" in e.detail.lower(),
            "passwords_mismatch": "no coinciden" in e.detail.lower()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar contraseña: {str(e)}"
        )

@router.post("/password-reset/confirm-secure", tags=["auth"])
def password_reset_confirm_secure(
    dto: schemas.PasswordResetConfirmSecure,
    db: Session = Depends(get_db)
):
    """Confirmación segura de reset de contraseña via token de email (REQUIERE CONTRASEÑA ACTUAL)"""
    try:
        # Verificar token y obtener usuario antes de procesar
        email = services.verify_password_reset_token(dto.token)
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # VALIDACIÓN: Verificar que el usuario esté habilitado
        if not user.estado:
            raise HTTPException(
                status_code=403, 
                detail="No se puede restablecer la contraseña de una cuenta deshabilitada. "
                       "Contacte con el administrador."
            )
        
        result = services.secure_password_reset_confirm(
            db=db,
            token=dto.token,
            current_password=dto.current_password,
            new_password=dto.new_password,
            confirm_password=dto.confirm_password
        )
        return result
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail,
            "status_code": e.status_code,
            "expired": e.status_code == 400 and "expirado" in e.detail.lower(),
            "used": e.status_code == 400 and "utilizado" in e.detail.lower(),
            "disabled": e.status_code == 403 and "deshabilitada" in e.detail.lower(),
            "wrong_current": "contraseña actual" in e.detail.lower(),
            "password_reused": "ya hayas utilizado" in e.detail.lower(),
            "passwords_mismatch": "no coinciden" in e.detail.lower()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar contraseña: {str(e)}"
        )

# ═══════════════════════════════════════════════════════════════════
# ADMINISTRACIÓN DE TOKENS - SOLO PARA ADMIN
# ═══════════════════════════════════════════════════════════════════

@router.post("/password-reset/cleanup-cache", tags=["admin"])
def cleanup_reset_tokens_cache(
    current_user: models.Usuario = Depends(require_admin_polo)
):
    """Limpiar cache de tokens usados - Solo admin"""
    count_before = services.get_used_tokens_count()
    services.cleanup_used_tokens()
    return {
        "message": f"Cache limpiado. Tokens eliminados: {count_before}",
        "tokens_removed": count_before
    }

@router.get("/password-reset/cache-status", tags=["admin"])
def get_cache_status(
    current_user: models.Usuario = Depends(require_admin_polo)
):
    """Ver estado del cache de tokens - Solo admin"""
    return {
        "used_tokens_count": services.get_used_tokens_count(),
        "memory_usage": "En memoria del servidor"
    }
