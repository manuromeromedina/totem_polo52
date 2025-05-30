from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app.models import Empresa, Contacto, ServicioPolo, Lote, TipoContacto, TipoServicioPolo
from app import schemas, models
from app.schemas import EmpresaOut, EmpresaDetailOutPublic, ContactoOutPublic, VehiculoOut, ServicioOut, ServicioPoloOutPublic, LoteOut, LoteOutPublic
from app.routes.auth import require_public_role

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


@router.get("/search/contactos", response_model=list[ContactoOutPublic], summary="Buscar empresas por nombre y devolver solo los contactos")
def search_companies_contacts(
    name: str = None,  # Parametro para nombre de la empresa
    db: Session = Depends(get_db)
):
    query = db.query(Empresa)
    
    # Filtrar por nombre de empresa
    if name:
        query = query.filter(Empresa.nombre.ilike(f"%{name}%"))

    # Obtener las empresas filtradas
    companies = query.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")
    
    # Crear una lista de contactos de todas las empresas
    all_contacts = []
    for empresa in companies:
        for contacto in empresa.contactos:
            tipo_contacto = contacto.tipo_contacto.tipo if contacto.tipo_contacto else None  # Obtener el tipo de contacto
            all_contacts.append(
                schemas.ContactoOutPublic(
                    empresa_nombre=empresa.nombre,  # Nombre de la empresa
                    nombre=contacto.nombre,
                    telefono=contacto.telefono,
                    datos=contacto.datos,
                    direccion=contacto.direccion,
                    tipo_contacto=tipo_contacto  # Incluir el tipo de contacto
                )
                    
            )
        
    return all_contacts


@router.get("/search/lotes", response_model=list[LoteOutPublic], summary="Buscar empresas por nombre y devolver solo los lotes")
def search_companies_lotes(
    name: str = None,  # Parametro para nombre de la empresa
    db: Session = Depends(get_db)
):
    query = db.query(Empresa)
    
    # Filtrar por nombre de empresa
    if name:
        query = query.filter(Empresa.nombre.ilike(f"%{name}%"))

    # Obtener las empresas filtradas
    companies = query.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")
    
    # Crear una lista de lotes de todas las empresas
    all_lotes = []
    for empresa in companies:
        for servicio_polo in empresa.servicios_polo:
            for lote in servicio_polo.lotes:
                # Creamos el objeto LoteOutPublic manualmente
                lote_data = schemas.LoteOutPublic(
                    empresa_nombre=empresa.nombre,  # Asignamos el nombre de la empresa
                    lote=lote.lote,  # Asignamos el número del lote
                    manzana=lote.manzana  # Asignamos la manzana
                )
                all_lotes.append(lote_data)  # Añadimos el lote a la lista
    
    return all_lotes








