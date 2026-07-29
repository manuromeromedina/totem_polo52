#app/routes/google_auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from datetime import date
import os
import httpx
from urllib.parse import urlencode
from app import models, services
from app.routes.auth import get_db, require_admin_polo

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])

# Configuración base para construir redirect URIs consistentes
EXTERNAL_BASE_URL = os.getenv("EXTERNAL_BASE_URL", "http://localhost:8000").rstrip("/")
ROOT_PATH = os.getenv("ROOT_PATH", "")
ROOT_PATH = "" if ROOT_PATH == "/" else ROOT_PATH  # evitar doble slash
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:4200").rstrip("/")


def _frontend_redirect(path: str, **params) -> RedirectResponse:
    """
    Arma una URL de redirect al frontend con los parámetros correctamente
    url-encoded. Sin esto, valores controlados por el usuario (como el
    nombre de perfil de Google) podían romper la URL o inyectar parámetros
    extra en la query string.
    """
    query = urlencode({k: v for k, v in params.items() if v is not None})
    return RedirectResponse(url=f"{FRONTEND_BASE_URL}{path}?{query}")

# Configurar OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/login")
async def google_login(request: Request):
    """Iniciar login con Google - SIEMPRE pregunta qué email usar"""
    redirect_uri_env = os.getenv('GOOGLE_REDIRECT_URI')
    # Construir redirect con base + root_path si no se pasó explícito
    redirect_uri = redirect_uri_env or f"{EXTERNAL_BASE_URL}{ROOT_PATH}/auth/google/callback"
    
    # ✅ FORZAR SELECCIÓN DE CUENTA
    return await oauth.google.authorize_redirect(
        request, 
        redirect_uri,
        # Estos parámetros fuerzan que Google siempre pregunte qué cuenta usar
        prompt='select_account',  # Fuerza mostrar selector de cuentas
        access_type='offline'     # Opcional: para refresh tokens
    )

@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Callback de Google OAuth con bloqueos por estado de usuario/empresa"""
    try:
        # 1) Intercambiar el code por tokens
        token = await oauth.google.authorize_access_token(request)

        # 2) Obtener perfil
        user_info = token.get('userinfo')
        if not user_info:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {token["access_token"]}'}
                )
                user_info = r.json()

        email = user_info.get('email')
        name = user_info.get('name')
        if not email:
            raise HTTPException(status_code=400, detail="No se pudo obtener el email de Google")

        # 3) Buscar usuario interno por email
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()

        # 3.a) Si no existe, no loguear: redirigir a “pendiente de registro”
        if not user:
            return _frontend_redirect("/auth/pending", email=email, name=name)

        # 3.b) Bloquear si el usuario está inhabilitado
        if not user.estado:
            return _frontend_redirect("/auth/error", message="usuario_inhabilitado")

        # 3.c) Bloquear si la empresa está desactivada
        if not user.empresa or not user.empresa.estado:
            return _frontend_redirect("/auth/error", message="empresa_desactivada")

        # 4) OK: generar tu JWT y redirigir a éxito
        roles = (
            db.query(models.Rol.tipo_rol)
            .join(models.RolUsuario, models.Rol.id_rol == models.RolUsuario.id_rol)
            .filter(models.RolUsuario.id_usuario == user.id_usuario)
            .all()
        )
        rol = roles[0][0] if roles else "usuario"

        access_token = services.create_access_token(data={"sub": user.nombre})

        return _frontend_redirect("/auth/success", token=access_token, tipo_rol=rol)

    except Exception as e:
        print(f"Error en Google callback: {str(e)}")
        return _frontend_redirect("/auth/error", message="Error_de_autenticacion")


@router.post("/register-pending")
async def register_pending_google_user(
    email: str,
    name: str,
    cuil: int,
    id_rol: int,
    current_user: models.Usuario = Depends(require_admin_polo),
    db: Session = Depends(get_db)
):
    """Registrar usuario que se autenticó con Google pero no estaba en el sistema"""
    
    # Verificar que no exista el usuario
    if db.query(models.Usuario).filter(models.Usuario.email == email).first():
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    
    # Verificar que la empresa existe
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(status_code=400, detail="La empresa no existe")
    
    # Verificar que el rol existe
    rol = db.query(models.Rol).filter(models.Rol.id_rol == id_rol).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol inválido")
    
    # Generar contraseña automática (aunque use Google, puede necesitarla)
    generated_password = services.generate_random_password()
    hashed_password = services.hash_password(generated_password)
    
    # Crear usuario
    new_user = models.Usuario(
        email=email,
        nombre=name,
        contrasena=hashed_password,
        estado=True,
        fecha_registro=date.today(),
        cuil=cuil,
    )
    db.add(new_user)
    db.flush()
    
    # Asignar rol
    enlace = models.RolUsuario(
        id_usuario=new_user.id_usuario,
        id_rol=rol.id_rol
    )
    db.add(enlace)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Usuario registrado exitosamente", "usuario": new_user}

@router.post("/logout-google")
async def logout_google():
    """Logout que también sugiere limpiar sesión de Google"""
    return {
        "message": "Sesión cerrada. Para cambiar de cuenta, ve a accounts.google.com y cierra sesión.",
        "google_logout_url": "https://accounts.google.com/logout"
    }
