from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import date
from jose import JWTError, jwt

from app import models, schemas, services
from app.config import SessionLocal, SECRET_KEY, ALGORITHM

app = FastAPI(
    title="Totem Polo52 API",
    version="0.1.0",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(401, "Token inválido")
    user = db.query(models.Usuario).filter(models.Usuario.nombre == username).first()
    if not user:
        raise HTTPException(401, "Usuario no encontrado")
    return user

def require_admin_polo(
    current_user: models.Usuario = Depends(get_current_user),
    db:           Session       = Depends(get_db),
):
    # Busca el rol en tu tabla 'rol'. Si en tu BD el admin se llama "admin",
    # asegúrate de filtrar por ese tipo_rol.
    from app.models import Rol, RolUsuario
    admin_rol = db.query(Rol).filter(Rol.tipo_rol == "admin").first()
    if not admin_rol:
        raise HTTPException(403, "Falta rol 'admin' en la BD")
    enlace = db.query(RolUsuario).filter(
        RolUsuario.id_usuario == current_user.id_usuario,
        RolUsuario.id_rol     == admin_rol.id_rol
    ).first()
    if not enlace:
        raise HTTPException(403, "Se requiere rol 'admin'")
    return current_user

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.post("/register", tags=["auth"])
def register(dto: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(400, "Nombre ya existe")
    new = models.Usuario(
        nombre        = dto.nombre,
        contrasena    = services.hash_password(dto.password),
        estado        = "activo",
        fecha_registro= date.today(),
        cuil          = dto.cuil,
    )
    db.add(new)
    db.commit()
    return {"message": "Usuario creado"}

@app.post(
    "/login",
    response_model=schemas.Token, 
    tags=["auth"],
    summary="Login (OAuth2 password flow)"
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db:        Session                  = Depends(get_db),
):
    user = db.query(models.Usuario).filter(models.Usuario.nombre == form_data.username).first()
    if not user or not services.verify_password(form_data.password, user.contrasena):
        raise HTTPException(401, "Credenciales inválidas")
    token = services.create_access_token({"sub": user.nombre})
    return {"access_token": token, "token_type": "bearer"}

# ─── ADMIN_POLO ──────────────────────────────────────────────────────────────
from app.routes.admin_users import router as admin_users_router
app.include_router(
    admin_users_router,
    prefix="/users",
    tags=["admin_polo"],
    dependencies=[Depends(require_admin_polo)]
)

from app.routes.admin_company import router as admin_company_router

app.include_router(
    admin_company_router,
    prefix="/companies",
    tags=["admin_polo"],
    dependencies=[Depends(require_admin_polo)]
)


# ─── ROOT ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
def read_root():
    return {"message": "Bienvenido al API Polo52"}

from app.routes.roles import router as roles_router
app.include_router(roles_router)

