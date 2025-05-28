from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app.models import Empresa, Contacto, ServicioPolo, Lote, TipoContacto, TipoServicioPolo
from app import schemas, models
from app.schemas import EmpresaOut, EmpresaDetailOutPublic, ContactoOutPublic, VehiculoOut, ServicioOut, ServicioPoloOutPublic, LoteOut
from app.routes.auth import require_public_role  # Asegúrate de que esté implementada correctamente

router = APIRouter(
    prefix="/public",  # Para que todas las rutas sean de tipo /public/...
    tags=["public"],
    dependencies=[Depends(require_public_role)],  # Solo accesible por usuarios con rol 'publico'
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/search", response_model=list[EmpresaDetailOutPublic], summary="Buscar empresas por nombre, rubro o servicio_polo")
def search_companies(
    name: str = None,  # Parametro para nombre de la empresa
    rubro: str = None,  # Parametro para rubro
    servicio_polo: str = None,  # Parametro para tipo de servicio de polo
    db: Session = Depends(get_db)
):
    query = db.query(Empresa)
    
    # Filtrar por nombre
    if name:
        query = query.filter(Empresa.nombre.ilike(f"%{name}%"))
    
    # Filtrar por rubro
    if rubro:
        query = query.filter(Empresa.rubro.ilike(f"%{rubro}%"))
    
    # Filtrar por tipo de servicio_polo (aquí cambiamos el filtro para que sea por TipoServicioPolo)
    if servicio_polo:
        # Realizamos el join con ServicioPolo y luego con TipoServicioPolo para filtrar por tipo
        query = query.join(ServicioPolo).join(TipoServicioPolo).filter(TipoServicioPolo.tipo.ilike(f"%{servicio_polo}%"))

    # Obtener las empresas filtradas
    companies = query.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")
    
    # Crear la lista de empresas con detalles completos
    empresa_details = []
    for empresa in companies:
        empresa_details.append(build_empresa_detail(empresa))
    
    return empresa_details


# Ruta para obtener una lista completa de empresas con todos los detalles de sus contactos, servicios, y lotes
@router.get("/all", response_model=list[EmpresaDetailOutPublic], summary="Obtener todas las empresas con detalles completos")
def get_all_companies(db: Session = Depends(get_db)):
    empresas = db.query(Empresa).all()
    if not empresas:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")
    
    empresa_details = []
    for empresa in empresas:
        # Obtener los detalles completos de cada empresa
        empresa_details.append(build_empresa_detail(empresa))
    
    return empresa_details


def build_empresa_detail(emp: models.Empresa) -> schemas.EmpresaDetailOut:
    # Creamos las listas para cada relación de la empresa

    conts = []
    for c in emp.contactos:
        tipo_contacto = c.tipo_contacto.tipo if c.tipo_contacto else None  # Obtener el tipo de contacto
        conts.append(
            schemas.ContactoOutPublic(
                nombre=c.nombre,
                telefono=c.telefono,
                datos=c.datos,
                direccion=c.direccion,
                tipo_contacto=tipo_contacto  # Incluir el tipo de contacto
            )
        )

    # Servicios asociados al Polo (asegurándose de que siempre haya una lista, incluso vacía)
    servicios_polo = []
    for esp in emp.servicios_polo:
        svc = esp  # Servicio Polo asociado a la empresa
        tipo_servicio_polo = svc.tipo_servicio.tipo if svc.tipo_servicio else None  # Tipo de servicio del Polo
        # Lotes asociados al servicio del polo
        lotes = [schemas.LoteOut.from_orm(l) for l in svc.lotes] if svc.lotes else []

        servicios_polo.append(
            schemas.ServicioPoloOutPublic(
                nombre=svc.nombre,
                horario=svc.horario,
                propietario=svc.propietario,
                tipo_servicio_polo=tipo_servicio_polo,  # Incluir el tipo de servicio del Polo
                lotes=lotes  # Incluir los lotes relacionados
            )
        )

    # Ahora armamos y devolvemos el objeto con los detalles completos de la empresa
    return schemas.EmpresaDetailOutPublic(
        nombre=emp.nombre,
        rubro=emp.rubro,
        fecha_ingreso=emp.fecha_ingreso,
        horario_trabajo=emp.horario_trabajo,
        contactos=conts,
        servicios_polo=servicios_polo  # Siempre pasa una lista, aunque esté vacía
    )
