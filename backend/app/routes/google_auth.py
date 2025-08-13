#app/routes/google_auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from datetime import date
import os
import httpx
from app.config import SessionLocal
from app import models, services
from app.routes.auth import get_db, require_admin_polo

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])

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
    """Iniciar login con Google"""
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Callback de Google OAuth"""
    try:
        # Obtener token de Google
        token = await oauth.google.authorize_access_token(request)
        
        # Obtener información del usuario
        user_info = token.get('userinfo')
        if not user_info:
            # Si no viene en el token, hacer request adicional
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {token["access_token"]}'}
                )
                user_info = response.json()
        
        email = user_info.get('email')
        name = user_info.get('name')
        
        if not email:
            raise HTTPException(status_code=400, detail="No se pudo obtener el email de Google")
        
        # Buscar usuario existente por email
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        
        if user:
            # Usuario existente - generar token
            access_token = services.create_access_token(data={"sub": user.nombre})
            
            # Obtener rol del usuario
            roles = (
                db.query(models.Rol.tipo_rol)
                .join(models.RolUsuario, models.Rol.id_rol == models.RolUsuario.id_rol)
                .filter(models.RolUsuario.id_usuario == user.id_usuario)
                .all()
            )
            rol = roles[0][0] if roles else "usuario"
            
            # Redireccionar al frontend con el token
            frontend_url = f"http://localhost:4200/auth/success?token={access_token}&tipo_rol={rol}"
            return RedirectResponse(url=frontend_url)
        else:
            # Usuario nuevo - mostrar mensaje de que necesita ser registrado
            frontend_url = f"http://localhost:4200/auth/pending?email={email}&name={name}"
            return RedirectResponse(url=frontend_url)
            
    except Exception as e:
        print(f"Error en Google callback: {str(e)}")
        # Redireccionar al frontend con error
        frontend_url = f"http://localhost:4200/auth/error?message=Error_de_autenticacion"
        return RedirectResponse(url=frontend_url)

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
