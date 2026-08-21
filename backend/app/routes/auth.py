#auth.py
from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from jose import JWTError, jwt
from datetime import date, datetime, timedelta
import os
from app.config import get_db, SECRET_KEY, ALGORITHM
from app import models, schemas, services
from app.models import Usuario
from app.schemas import PasswordResetRequest, PasswordResetConfirm, PasswordResetConfirmSecure, ChangePasswordDirect, ForgotPasswordReset
from app.rate_limit import rate_limit

router = APIRouter()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:4200").rstrip("/")

# OAuth2PasswordBearer para manejar el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y UTILIDADES
# ═══════════════════════════════════════════════════════════════════

def _empresa_inactiva_detail(empresa: models.Empresa) -> str:
    """Mensaje de bloqueo de login/uso de API según por qué la empresa
    (y por lo tanto sus usuarios) está inactiva."""
    if empresa.estado_solicitud == "pendiente":
        return "Tu registro está pendiente de aprobación por el administrador del Polo."
    if empresa.estado_solicitud == "rechazada":
        return "Tu solicitud de registro fue rechazada. Contactá al administrador del Polo para más información."
    return "La empresa asociada está desactivada."


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

        # Empresa desactivada / pendiente / rechazada
        if not user.empresa or not user.empresa.estado:
            raise HTTPException(
                status_code=403,
                detail=_empresa_inactiva_detail(user.empresa) if user.empresa else "La empresa asociada está desactivada."
            )

        return user
    except JWTError:
        raise HTTPException(401, "Token inválido")


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

@router.post("/register", tags=["auth"], dependencies=[Depends(rate_limit("register", max_requests=5, window_seconds=60))])
def register(dto: schemas.EmpresaRegisterRequest, db: Session = Depends(get_db)):
    """
    Autoregistro público: crea la empresa y su usuario admin_empresa juntos,
    ambos pendientes de aprobación por admin_polo (empresa.estado=False,
    estado_solicitud='pendiente'). No hay login automático: recién puede
    ingresar una vez aprobada.
    """
    if db.query(models.Empresa).filter(models.Empresa.cuil == dto.cuil).first():
        raise HTTPException(status_code=400, detail="Ya existe una empresa con ese CUIL")
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.usuario_nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre")
    if db.query(models.Usuario).filter(models.Usuario.email == dto.email).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")

    rol_admin_empresa = db.query(models.Rol).filter(models.Rol.tipo_rol == "admin_empresa").first()
    if not rol_admin_empresa:
        raise HTTPException(status_code=500, detail="El rol admin_empresa no está configurado")

    empresa = models.Empresa(
        cuil=dto.cuil,
        nombre=dto.nombre,
        rubro=dto.rubro,
        cant_empleados=dto.cant_empleados,
        observaciones=dto.observaciones,
        fecha_ingreso=date.today(),
        horario_trabajo=dto.horario_trabajo,
        estado=False,
        estado_solicitud="pendiente",
    )
    db.add(empresa)
    db.flush()

    nuevo_usuario = models.Usuario(
        nombre=dto.usuario_nombre,
        email=dto.email,
        contrasena=services.hash_password(dto.password),
        estado=True,
        mostrar_bienvenida=True,
        fecha_registro=date.today(),
        cuil=empresa.cuil,
    )
    db.add(nuevo_usuario)
    db.flush()

    db.add(models.RolUsuario(id_usuario=nuevo_usuario.id_usuario, id_rol=rol_admin_empresa.id_rol))
    db.commit()

    email_sent = services.send_registration_received_email(
        email=dto.email,
        nombre=dto.usuario_nombre,
        nombre_empresa=dto.nombre,
    )
    if not email_sent:
        print(f"Registro creado pero email no enviado para: {dto.email}")

    return {
        "message": "Solicitud de registro recibida. Te avisaremos por email cuando sea aprobada."
    }

@router.post(
    "/login",
    response_model=schemas.Token,
    tags=["auth"],
    dependencies=[Depends(rate_limit("login", max_requests=10, window_seconds=60))],
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
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

    # Empresa desactivada / pendiente / rechazada
    if not user.empresa or not user.empresa.estado:
        raise HTTPException(
            status_code=403,
            detail=_empresa_inactiva_detail(user.empresa) if user.empresa else "La empresa asociada está desactivada."
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

    return {
        # Campos originales
        "access_token": access_token,
        "token_type": "bearer",
        "tipo_rol": rol,
        "mostrar_bienvenida": bool(user.mostrar_bienvenida),
        # Alias adicionales para compatibilidad con frontends que esperan otros nombres
        "token": access_token,
        "role": rol,
        "user": {
            "id": user.id_usuario,
            "nombre": user.nombre,
            "email": user.email,
        },
        "success": True,
    }


@router.post("/logout", tags=["auth"], summary="Cerrar sesión")
def logout(
    current_user: models.Usuario = Depends(get_current_user)
):
    return {"message": "Sesión cerrada correctamente"}


@router.post("/bienvenida-vista", tags=["auth"], summary="Marcar como visto el aviso de bienvenida del primer login")
def marcar_bienvenida_vista(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.mostrar_bienvenida = False
    db.commit()
    return {"message": "Aviso de bienvenida marcado como visto"}

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
            services.send_password_change_notification(
                email=current_user.email,
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
            services.send_password_change_failure_notification(
                email=current_user.email,
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
            services.send_password_change_failure_notification(
                email=current_user.email,
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

@router.post(
    "/forgot-password",
    tags=["auth"],
    dependencies=[Depends(rate_limit("forgot-password", max_requests=5, window_seconds=60))],
)
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
    
    reset_link = f"{FRONTEND_BASE_URL}/reset-password?token={token}"

    if not services.send_password_reset_email(email=user.email, nombre=user.nombre, reset_link=reset_link):
        raise HTTPException(status_code=500, detail="Error enviando email")

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
