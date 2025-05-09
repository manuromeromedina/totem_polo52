# app/routes/admin_company.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from app.config import SessionLocal                # para crear la sesión
from app.models import Empresa                      # tu modelo de empresa
from app.schemas import EmpresaOut, EmpresaCreate, EmpresaUpdate
from app.main import require_admin_polo             # tu dependencia RBAC

router = APIRouter(
    prefix="/companies",
    tags=["admin_polo"],
    dependencies=[Depends(require_admin_polo)],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/",
    response_model=List[EmpresaOut],
    summary="Listar todas las empresas"
)
def list_companies(db: Session = Depends(get_db)):
    return db.query(Empresa).all()

@router.post(
    "/",
    response_model=EmpresaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva empresa"
)
def create_company(dto: EmpresaCreate, db: Session = Depends(get_db)):
    if db.query(Empresa).filter(Empresa.cuil == dto.cuil).first():
        raise HTTPException(400, "Ya existe una empresa con ese CUIL")
    new = Empresa(
        cuil=dto.cuil,
        nombre=dto.nombre,
        rubro=dto.rubro,
        cant_empleados=dto.cant_empleados,
        observaciones=dto.observaciones,
        fecha_ingreso=dto.fecha_ingreso or date.today(),
        horario_trabajo=dto.horario_trabajo
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@router.put(
    "/{cuil}",
    response_model=EmpresaOut,
    summary="Actualizar una empresa existente"
)
def update_company(
    cuil: int,
    dto: EmpresaUpdate,
    db: Session = Depends(get_db)
):
    emp = db.query(Empresa).filter(Empresa.cuil == cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")

    data = dto.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(emp, field, val)

    db.commit()
    db.refresh(emp)
    return emp

@router.delete(
    "/{cuil}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una empresa"
)
def delete_company(
    cuil: int,
    db: Session = Depends(get_db)
):
    emp = db.query(Empresa).filter(Empresa.cuil == cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")
    db.delete(emp)
    db.commit()
