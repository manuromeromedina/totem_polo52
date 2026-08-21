#app/routes/directory.py
"""
Directorio de empresas del parque, accesible a cualquier usuario logueado
(admin_polo, admin_empresa o publico) para facilitar el contacto y el
networking entre inquilinos del Parque Industrial Polo 52.

Estas rutas vivian antes en admin_users.py pero quedaban atrapadas detras
de la dependencia require_admin_polo de ese router, pese a estar pensadas
como consultas generales ("para consulta publica"). Se movieron aca con
una dependencia mas permisiva (cualquier usuario autenticado).
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, selectinload

from app.config import get_db
from app import models, schemas
from app.models import Empresa, ServicioPolo, TipoServicioPolo
from app.schemas import EmpresaDetailOutPublic, ContactoOutPublic, LoteOutPublic
from app.routes.auth import get_current_user
from app.routes.admin_users import POLO_CUIL

router = APIRouter(
    prefix="",
    tags=["Directorio"],
    dependencies=[Depends(get_current_user)],
)

# Precarga usada por los endpoints que arman EmpresaDetailOutPublic: sin esto,
# cada empresa listada dispara consultas separadas por sus contactos,
# servicios del polo e info comercial (N+1).
EMPRESA_DETAIL_EAGER_OPTIONS = (
    selectinload(models.Empresa.contactos).selectinload(models.Contacto.tipo_contacto),
    selectinload(models.Empresa.servicios_polo).selectinload(models.ServicioPolo.tipo_servicio),
    selectinload(models.Empresa.servicios_polo).selectinload(models.ServicioPolo.lotes),
    selectinload(models.Empresa.info_comercial),
)


def build_empresa_detail_public(emp: models.Empresa) -> schemas.EmpresaDetailOutPublic:
    """Construir detalle publico de empresa con contactos, servicios polo e info comercial"""
    conts = []
    for c in emp.contactos:
        tipo_contacto = c.tipo_contacto.tipo if c.tipo_contacto else None
        conts.append(
            schemas.ContactoOutPublic(
                empresa_nombre=emp.nombre,
                nombre=c.nombre,
                telefono=c.telefono,
                datos=c.datos,
                direccion=c.direccion,
                tipo_contacto=tipo_contacto
            )
        )

    servicios_polo = []
    for esp in emp.servicios_polo:
        svc = esp
        tipo_servicio_polo = svc.tipo_servicio.tipo if svc.tipo_servicio else None
        lotes = [schemas.LoteOut.from_orm(l) for l in svc.lotes] if svc.lotes else []

        servicios_polo.append(
            schemas.ServicioPoloOutPublic(
                nombre=svc.nombre,
                horario=svc.horario,
                propietario=svc.propietario,
                tipo_servicio_polo=tipo_servicio_polo,
                lotes=lotes
            )
        )

    info_comercial = (
        schemas.InfoComercialOut.from_orm(emp.info_comercial)
        if emp.info_comercial
        else None
    )

    return schemas.EmpresaDetailOutPublic(
        cuil=emp.cuil,
        nombre=emp.nombre,
        rubro=emp.rubro,
        cant_empleados=emp.cant_empleados,
        observaciones=emp.observaciones,
        fecha_ingreso=emp.fecha_ingreso,
        horario_trabajo=emp.horario_trabajo,
        contactos=conts,
        servicios_polo=servicios_polo,
        info_comercial=info_comercial,
    )


@router.get(
    "/empresas/directorio",
    response_model=List[EmpresaDetailOutPublic],
    summary="Directorio de empresas del parque (nombre, contacto comercial, telefono y datos comerciales)",
)
def get_empresas_directorio(db: Session = Depends(get_db)):
    """Listar todas las empresas activas con su contacto comercial y datos comerciales, para networking entre inquilinos"""
    empresas = (
        db.query(Empresa)
        .options(*EMPRESA_DETAIL_EAGER_OPTIONS)
        .filter(Empresa.estado == True)
        .filter(Empresa.cuil != POLO_CUIL)
        .all()
    )
    return [build_empresa_detail_public(empresa) for empresa in empresas]


@router.get("/search", response_model=List[EmpresaDetailOutPublic], summary="Buscar empresas por criterios especificos")
def search_companies(
    name: Optional[str] = None,
    rubro: Optional[str] = None,
    servicio_polo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Buscar empresas por nombre, rubro o tipo de servicio del polo"""
    query = db.query(Empresa).options(*EMPRESA_DETAIL_EAGER_OPTIONS)

    if name:
        query = query.filter(Empresa.nombre.ilike(f"%{name}%"))

    if rubro:
        query = query.filter(Empresa.rubro.ilike(f"%{rubro}%"))

    if servicio_polo:
        query = query.join(ServicioPolo).join(TipoServicioPolo).filter(
            TipoServicioPolo.tipo.ilike(f"%{servicio_polo}%")
        )

    companies = query.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")

    return [build_empresa_detail_public(empresa) for empresa in companies]


@router.get("/search/contactos", response_model=List[ContactoOutPublic], summary="Buscar contactos por empresa")
def search_companies_contacts(name: Optional[str] = None, db: Session = Depends(get_db)):
    """Buscar empresas por nombre y devolver solo los contactos"""
    query = db.query(Empresa).options(
        selectinload(Empresa.contactos).selectinload(models.Contacto.tipo_contacto)
    )

    if name:
        query = query.filter(Empresa.nombre.ilike(f"%{name}%"))

    companies = query.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")

    all_contacts = []
    for empresa in companies:
        for contacto in empresa.contactos:
            tipo_contacto = contacto.tipo_contacto.tipo if contacto.tipo_contacto else None
            all_contacts.append(
                schemas.ContactoOutPublic(
                    empresa_nombre=empresa.nombre,
                    nombre=contacto.nombre,
                    telefono=contacto.telefono,
                    datos=contacto.datos,
                    direccion=contacto.direccion,
                    tipo_contacto=tipo_contacto
                )
            )

    return all_contacts


@router.get("/search/lotes", response_model=List[LoteOutPublic], summary="Buscar lotes por empresa")
def search_companies_lotes(name: Optional[str] = None, db: Session = Depends(get_db)):
    """Buscar empresas por nombre y devolver solo los lotes"""
    query = db.query(Empresa).options(
        selectinload(Empresa.servicios_polo).selectinload(models.ServicioPolo.lotes)
    )

    if name:
        query = query.filter(Empresa.nombre.ilike(f"%{name}%"))

    companies = query.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")

    all_lotes = []
    for empresa in companies:
        for servicio_polo in empresa.servicios_polo:
            for lote in servicio_polo.lotes:
                lote_data = schemas.LoteOutPublic(
                    empresa_nombre=empresa.nombre,
                    lote=lote.lote,
                    manzana=lote.manzana
                )
                all_lotes.append(lote_data)

    return all_lotes
