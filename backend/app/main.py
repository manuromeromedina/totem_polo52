# app/main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import date
from jose import JWTError, jwt

from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app import models, schemas, services

app = FastAPI(
    title="Totem Polo52 API",
    version="0.1.0",
)

# --- OAuth2 bearer con login en /login ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Sesión de DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Extrae usuario de JWT ---
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(models.Usuario).filter(models.Usuario.nombre == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return user

# --- RBAC: sólo admin_polo ---
def require_admin_polo(
    current_user: models.Usuario = Depends(get_current_user),
    db:           Session       = Depends(get_db),
):
    from app.models import Rol, RolUsuario

    admin_rol = db.query(Rol).filter(Rol.tipo_rol == "admin_polo").first()
    if not admin_rol:
        raise HTTPException(status_code=403, detail="Falta rol 'admin_polo' en la BD")

    enlace = db.query(RolUsuario).filter(
        RolUsuario.id_usuario == current_user.id_usuario,
        RolUsuario.id_rol     == admin_rol.id_rol
    ).first()
    if not enlace:
        raise HTTPException(status_code=403, detail="Se requiere rol 'admin_polo'")

    return current_user

# --- RBAC: sólo admin_empresa ---
def require_empresa_role(
    current_user: models.Usuario = Depends(get_current_user),
    db:           Session       = Depends(get_db),
):
    from app.models import Rol, RolUsuario

    emp_rol = db.query(Rol).filter(Rol.tipo_rol == "admin_empresa").first()
    if not emp_rol:
        raise HTTPException(status_code=403, detail="Rol 'admin_empresa' no existe en la BD")

    enlace = db.query(RolUsuario).filter(
        RolUsuario.id_usuario == current_user.id_usuario,
        RolUsuario.id_rol     == emp_rol.id_rol
    ).first()
    if not enlace:
        raise HTTPException(status_code=403, detail="Se requiere rol 'admin_empresa'")

    return current_user

# ─── AUTH ENDPOINTS ───────────────────────────────────────────────────────────

@app.post("/register", tags=["auth"])
def register(dto: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Nombre ya existe")
    new = models.Usuario(
        nombre         = dto.nombre,
        contrasena     = services.hash_password(dto.password),
        estado         = "activo",
        fecha_registro = date.today(),
        cuil           = dto.cuil,
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
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    access_token = services.create_access_token(data={"sub": user.nombre})
    return {"access_token": access_token, "token_type": "bearer"}

# ─── ADMIN_POLO ROUTERS ────────────────────────────────────────────────────────

from app.routes.admin_users   import router as admin_users_router
from app.routes.admin_company import router as admin_company_router

app.include_router(
    admin_users_router,
    prefix="/users",
    tags=["admin_polo"],
    dependencies=[Depends(require_admin_polo)],
)

app.include_router(
    admin_company_router,
    prefix="/companies",
    tags=["admin_polo"],
    dependencies=[Depends(require_admin_polo)],
)

# ─── EMPRESA ROUTERS ──────────────────────────────────────────────────────────

from app.routes.company_user import router as company_user_router

app.include_router(
    company_user_router,
    tags=["empresa"],
    dependencies=[Depends(require_empresa_role)],
)

# ─── ROLES ROUTER ────────────────────────────────────────────────────────────

from app.routes.roles import router as roles_router

app.include_router(
    roles_router,
    prefix="/roles",
    tags=["roles"],
)

# ─── RAÍZ ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
def read_root():
    return {"message": "Bienvenido al API Polo52"}
