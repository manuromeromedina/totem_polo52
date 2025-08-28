#auth.py
from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from jose import JWTError, jwt
from datetime import date
from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app import models, schemas, services
from app.models import Usuario
from app.schemas import PasswordResetRequest, PasswordResetConfirm, PasswordResetConfirmSecure, ChangePasswordDirect
from email.mime.text import MIMEText
import smtplib
from app.config import settings
from app.services import (
    secure_password_reset_confirm, 
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
        return user
    except JWTError:
        raise HTTPException(401, "Token inválido")

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
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (db.query(models.Usuario).filter(
        or_(models.Usuario.nombre == form_data.username, 
            models.Usuario.email == form_data.username)
    ).first())
    
    if not user or not services.verify_password(form_data.password, user.contrasena):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # Obtener roles del usuario
    roles = (
        db.query(models.Rol.tipo_rol)
        .join(models.RolUsuario, models.Rol.id_rol == models.RolUsuario.id_rol)
        .filter(models.RolUsuario.id_usuario == user.id_usuario)
        .all()
    )

    # Extraer primer rol o asignar un valor por defecto
    rol = roles[0][0] if roles else "usuario"

    access_token = services.create_access_token(data={"sub": user.nombre})
    return {"access_token": access_token, "token_type": "bearer", "tipo_rol": rol}

@router.post("/logout", tags=["auth"], summary="Cerrar sesión")
def logout(current_user: models.Usuario = Depends(get_current_user)):
    return {"message": "Sesión cerrada correctamente"}

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
    Cambio directo de contraseña (sin email, requiere estar logueado)
    """
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
        
        return {
            "success": True,
            "message": "Contraseña actualizada correctamente"
        }
        
    except HTTPException as e:
        db.rollback()
        return {
            "success": False,
            "error": e.detail,
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
# RECUPERACIÓN DE CONTRASEÑA VIA EMAIL (USUARIO NO LOGUEADO)
# ═══════════════════════════════════════════════════════════════════

@router.post("/forgot-password", tags=["auth"])
def forgot_password(dto: PasswordResetRequest, db: Session = Depends(get_db)):
    """Solicitar reset de contraseña via email (para usuarios no logueados)"""
    user = db.query(models.Usuario).filter(models.Usuario.email == dto.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email no registrado")
    
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
            "used": "utilizado" in e.detail.lower()
        }

@router.post("/password-reset/confirm-secure", tags=["auth"])
def password_reset_confirm_secure(
    dto: schemas.PasswordResetConfirmSecure,
    db: Session = Depends(get_db)
):
    """Confirmación segura de reset de contraseña via token de email"""
    try:
        result = services.secure_password_reset_confirm(
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