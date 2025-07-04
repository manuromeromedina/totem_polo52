# tipos.py - Nuevo archivo para los endpoints de tipos
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app import models, schemas
from typing import List

router = APIRouter(
    prefix="/tipos",
    tags=["Tipos"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Tipos de Vehículo
@router.get("/vehiculo", response_model=List[schemas.TipoVehiculoOut])
def get_tipos_vehiculo(db: Session = Depends(get_db)):
    """Obtener todos los tipos de vehículo"""
    return db.query(models.TipoVehiculo).all()

# Tipos de Servicio
@router.get("/servicio", response_model=List[schemas.TipoServicioOut])
def get_tipos_servicio(db: Session = Depends(get_db)):
    """Obtener todos los tipos de servicio"""
    return db.query(models.TipoServicio).all()

# Tipos de Contacto
@router.get("/contacto", response_model=List[schemas.TipoContactoOut])
def get_tipos_contacto(db: Session = Depends(get_db)):
    """Obtener todos los tipos de contacto"""
    return db.query(models.TipoContacto).all()

# Tipos de Servicio del Polo
@router.get("/servicio-polo", response_model=List[schemas.TipoServicioPoloOut])
def get_tipos_servicio_polo(db: Session = Depends(get_db)):
    """Obtener todos los tipos de servicio del polo"""
    return db.query(models.TipoServicioPolo).all()

