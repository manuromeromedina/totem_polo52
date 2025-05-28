from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from jose import JWTError, jwt
from datetime import date  # Agregada para usar la fecha actual en el registro
from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app import models, schemas, services
from app.models import Usuario

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


# ─── AUTH ENDPOINTS ───────────────────────────────────────────────────────────

@router.post("/register", tags=["auth"])
def register(dto: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Nombre ya existe")
    new = models.Usuario(
        nombre         = dto.nombre,
        contrasena     = services.hash_password(dto.password),
        estado         = "activo",
        fecha_registro = date.today(),  # Usamos la fecha actual
        cuil           = dto.cuil,
    )
    db.add(new)
    db.commit()
    return {"message": "Usuario creado"}

@router.post(
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
