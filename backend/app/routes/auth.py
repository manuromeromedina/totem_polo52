#app/routes/auth.py
from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from jose import JWTError, jwt
from datetime import date  # Agregada para usar la fecha actual en el registro
from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app import models, schemas, services
from app.models import Usuario
from app.schemas import PasswordResetRequest, PasswordResetConfirm
from email.mime.text import MIMEText
import smtplib
from app import models, services  # Ajusta los imports según tu estructura
from app.config import settings  # Para las variables de entorno

router = APIRouter()

# OAuth2PasswordBearer para manejar el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Base de datos ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Extrae usuario de JWT ---
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db)
) -> models.Usuario:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nombre  = payload.get("sub")
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


# --- Roles ---
def require_admin_polo(
    current_user: Usuario = Depends(get_current_user),
    db:           Session = Depends(get_db)
) -> Usuario:
    # Cargar roles de usuario
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
    db:           Session = Depends(get_db)
) -> Usuario:
    # Cargar roles de usuario
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
    db:           Session = Depends(get_db)
) -> Usuario:
    # Cargar roles de usuario
    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.roles))
        .filter(Usuario.id_usuario == current_user.id_usuario)
        .first()
    )
    if not any(r.tipo_rol == "publico" for r in user.roles):
        raise HTTPException(403, "Se requiere rol 'publico'")
    return current_user

# --- Rutas Auth ---
 
@router.post("/login", response_model=schemas.Token, tags=["auth"])
def login(
     form_data: OAuth2PasswordRequestForm = Depends(),
     db:        Session                  = Depends(get_db),
 ):
    user = (db.query(models.Usuario).filter(or_(models.Usuario.nombre == form_data.username, models.Usuario.email  == form_data.username)).first())
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
    # El JWT es stateless, solo necesitamos devolver un mensaje indicando que se ha cerrado la sesión
    return {"message": "Sesión cerrada correctamente"}

# Actualizar solo estas rutas en tu auth.py existente

@router.post("/password-reset/verify-token", tags=["auth"])
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Verificar si un token de reset es válido sin hacer cambios
    Ahora incluye verificación de uso único
    """
    try:
        email = services.verify_password_reset_token(token)  # Solo verifica, NO consume
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        return {
            "valid": True,
            "message": "Token válido",
            "email_hint": f"{email[:3]}***@{email.split('@')[1]}"
        }
        
    except HTTPException as e:
        return {
            "valid": False,
            "error": e.detail,
            "expired": "expirado" in e.detail.lower(),
            "used": "utilizado" in e.detail.lower()  # ✅ Nuevo: detectar tokens usados
        }

@router.post("/password-reset/confirm", tags=["auth"])
def password_reset_confirm(dto: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Confirmar reset de contraseña con protección de uso único
    """
    try:
        # ✅ USAR consume_password_reset_token que verifica Y marca como usado
        email = services.consume_password_reset_token(dto.token)
        
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Actualizar la contraseña
        user.contrasena = services.hash_password(dto.new_password)
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "message": "Contraseña actualizada correctamente. Este enlace ya no es válido."
        }
        
    except HTTPException as e:
        db.rollback()
        return {
            "success": False,
            "error": e.detail,
            "expired": e.status_code == 400 and "expirado" in e.detail.lower(),
            "used": e.status_code == 400 and "utilizado" in e.detail.lower()  # ✅ Nuevo
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno al actualizar contraseña: {str(e)}"
        )

# ✅ OPCIONAL: Endpoint para limpiar cache (solo para admin o testing)
@router.post("/password-reset/cleanup-cache", tags=["admin"])
def cleanup_reset_tokens_cache(
    current_user: models.Usuario = Depends(require_admin_polo)  # Solo admin
):
    """Limpiar cache de tokens usados"""
    count_before = services.get_used_tokens_count()
    services.cleanup_used_tokens()
    return {
        "message": f"Cache limpiado. Tokens eliminados: {count_before}",
        "tokens_removed": count_before
    }

# ✅ OPCIONAL: Endpoint para monitorear cache
@router.get("/password-reset/cache-status", tags=["admin"])
def get_cache_status(
    current_user: models.Usuario = Depends(require_admin_polo)  # Solo admin
):
    """Ver estado del cache de tokens"""
    return {
        "used_tokens_count": services.get_used_tokens_count(),
        "memory_usage": "En memoria del servidor"
    }

@router.post("/password-reset/request", tags=["auth"])
def password_reset_request(dto: PasswordResetRequest, db: Session = Depends(get_db)):
    """Solicitar reset de contraseña - tiempo de expiración personalizable"""
    user = db.query(models.Usuario).filter(models.Usuario.email == dto.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email no registrado")
    
    # Puedes ajustar el tiempo de expiración aquí
    RESET_TOKEN_EXPIRE_MINUTES = 30  # 1 hora (puedes cambiar a 30, 120, etc.)
    
    token = services.create_password_reset_token(
        user.email, 
        expires_minutes=RESET_TOKEN_EXPIRE_MINUTES
    )
    
    reset_link = f"http://localhost:4200/password-reset?token={token}"
    
    # Email con información de expiración
    expire_time = RESET_TOKEN_EXPIRE_MINUTES // 30 if RESET_TOKEN_EXPIRE_MINUTES >= 30 else RESET_TOKEN_EXPIRE_MINUTES
    expire_unit = "horas" if RESET_TOKEN_EXPIRE_MINUTES >= 30 else "minutos"
    
    email_body = f"""
    Hola {user.nombre},

    Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace para continuar:

    {reset_link}

    IMPORTANTE: Este enlace expirará en {expire_time} {expire_unit} por seguridad.

    Si no solicitaste este cambio, puedes ignorar este email.

    Saludos,
    Equipo de Polo 52
    """
    
    msg = MIMEText(email_body)
    msg["Subject"] = "Restablecer Contraseña - Polo 52"
    msg["From"] = settings.EMAIL_USER
    msg["To"] = dto.email
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")
    
    return {
        "message": "Email de reset enviado correctamente",
        "expires_in_minutes": RESET_TOKEN_EXPIRE_MINUTES
    }



@router.post("/password-reset/request-logged-user", tags=["auth"])
def password_reset_request_logged_user(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Solicitar reset de contraseña para el usuario logueado"""
    token = services.create_password_reset_token(current_user.email)
    reset_link = f"http://localhost:4200/password-reset?token={token}"
    
    # Email setup
    msg = MIMEText(f"Hola {current_user.nombre},\n\nHas solicitado cambiar tu contraseña. Click en el siguiente enlace para continuar:\n\n{reset_link}\n\nSi no solicitaste este cambio, ignora este email.")
    msg["Subject"] = "Cambio de Contraseña - Polo 52"
    msg["From"] = settings.EMAIL_USER
    msg["To"] = current_user.email
    
    # Send email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando email: {str(e)}")
    
    return {"message": "Email de cambio de contraseña enviado exitosamente"}