from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from jose import JWTError, jwt

from app import models
from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app.models import Usuario
from app.schemas import UserOut

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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


def require_admin_role(
    current_user: Usuario = Depends(get_current_user),
    db:           Session = Depends(get_db)
) -> Usuario:
    # cargamos también sus roles
    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.roles))
        .filter(Usuario.id_usuario == current_user.id_usuario)
        .first()
    )
    if not any(r.tipo_rol == "admin_polo" for r in user.roles):
        raise HTTPException(403, "Se requiere rol admin_polo")
    return user
