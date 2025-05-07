# app/routes/roles.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.models import Rol
from app.schemas import RolOut
from app.config import SessionLocal
from app.main import require_admin_polo   # tu dependencia de RBAC

router = APIRouter(
    prefix="/roles",
    tags=["admin_polo"],
    dependencies=[Depends(require_admin_polo)],  # sólo admins pueden llamarlo
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/",
    response_model=List[RolOut],
    summary="Listar roles disponibles",
)
def list_roles(db: Session = Depends(get_db)):
    """
    Devuelve todos los roles que existen en la tabla `rol`.
    """
    return db.query(Rol).all()
