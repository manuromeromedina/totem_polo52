# app/routes/company_user.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import SessionLocal
from app import models, schemas, services
from app.main import get_current_user, require_empresa_role

router = APIRouter(
    prefix="",
    tags=["empresa"],
    dependencies=[Depends(require_empresa_role)],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1) GET /me
@router.get(
    "/me",
    response_model=schemas.MeOut,
    summary="Mis datos de usuario y empresa"
)
def read_me(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                    = Depends(get_db),
):
    empresa = (
        db.query(models.Empresa)
          .filter(models.Empresa.cuil == current_user.cuil)
          .first()
    )
    return schemas.MeOut(user=current_user, empresa=empresa)

# 2) PUT /me
@router.put(
    "/me",
    response_model=schemas.UserOut,
    summary="Actualizar mis datos de usuario"
)
def update_me(
    dto: schemas.UserUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                    = Depends(get_db),
):
    data = dto.model_dump(exclude_unset=True)
    # Si viene password, hasheamos con el servicio correcto
    if "password" in data:
        current_user.contrasena = services.hash_password(data.pop("password"))
    db.commit()
    db.refresh(current_user)
    return current_user

# 3) GET /companies/{cuil}/details
@router.get(
    "/companies/{cuil}/details",
    response_model=schemas.EmpresaOut,
    summary="Ficha completa de mi empresa"
)
def company_details(
    cuil: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                    = Depends(get_db),
):
    if current_user.cuil != cuil:
        raise HTTPException(403, "Sólo puedes ver tu propia empresa")
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")
    return empresa

# 4) PUT /companies/{cuil}
@router.put(
    "/companies/{cuil}",
    response_model=schemas.EmpresaOut,
    summary="Actualizar campos permisibles de mi empresa"
)
def company_update_self(
    cuil: int,
    dto: schemas.EmpresaSelfUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                    = Depends(get_db),
):
    if current_user.cuil != cuil:
        raise HTTPException(403, "No puedes editar otra empresa")
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")

    data = dto.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(empresa, field, val)

    db.commit()
    db.refresh(empresa)
    return empresa

# 5) GET /companies/{cuil}/internal
@router.get(
    "/companies/{cuil}/internal",
    response_model=schemas.InternalOut,
    summary="Datos internos de mi empresa"
)
def company_internal(
    cuil: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                    = Depends(get_db),
):
    if current_user.cuil != cuil:
        raise HTTPException(403, "Sólo puedes ver tu propia empresa")
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")

    return schemas.InternalOut(
        dotacion=empresa.cant_empleados,
        energia=None,   # reemplaza con la consulta real
        residuos=None   # reemplaza con la consulta real
    )
