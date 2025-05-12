# app/routes/public.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.config import SessionLocal
from app import models
from app.schemas import EmpresaPublicOut, ServicePublicOut

router = APIRouter(tags=["public"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/companies",
    response_model=List[EmpresaPublicOut],
    summary="Listar todas las empresas"
)
def list_companies(db: Session = Depends(get_db)):
    return db.query(models.Empresa).all()

@router.get(
    "/companies/{cuil}",
    response_model=EmpresaPublicOut,
    summary="Detalle de una empresa"
)
def get_company(cuil: int, db: Session = Depends(get_db)):
    emp = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")
    return emp

@router.get(
    "/companies/search",
    response_model=List[EmpresaPublicOut],
    summary="Buscar empresas por nombre, rubro o ubicación"
)
def search_companies(
    nombre:    Optional[str] = Query(None),
    rubro:     Optional[str] = Query(None),
    ubicacion: Optional[str] = Query(None),
    db:         Session      = Depends(get_db),
):
    q = db.query(models.Empresa)
    if nombre:
        q = q.filter(models.Empresa.nombre.ilike(f"%{nombre}%"))
    if rubro:
        q = q.filter(models.Empresa.rubro.ilike(f"%{rubro}%"))
    if ubicacion and hasattr(models.Empresa, "ubicacion"):
        q = q.filter(models.Empresa.ubicacion.ilike(f"%{ubicacion}%"))
    return q.all()

@router.get(
    "/polo/services",
    response_model=List[ServicePublicOut],
    summary="Listar servicios del Polo"
)
def list_services(db: Session = Depends(get_db)):
    return db.query(models.Servicio).all()

@router.get(
    "/polo/services/{service_id}",
    response_model=ServicePublicOut,
    summary="Detalle de un servicio del Polo"
)
def get_service(service_id: int, db: Session = Depends(get_db)):
    srv = db.query(models.Servicio).get(service_id)
    if not srv:
        raise HTTPException(404, "Servicio no encontrado")
    return srv
