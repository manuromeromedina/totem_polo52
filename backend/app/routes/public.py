# app/routes/public.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app import models, schemas

router = APIRouter(tags=["público"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/search_companies",
    response_model=list[schemas.CompanyFullOut],
    summary="Listar empresas (filtrable por nombre, rubro o tipo de servicio del polo)"
)
def list_companies_full(
    nombre:           str | None = Query(None, description="Filtro parcial por nombre de empresa"),
    rubro:            str | None = Query(None, description="Filtro parcial por rubro"),
    tipo_servicio:    str | None = Query(None, alias="servicio_tipo", description="Filtro parcial por tipo de servicio del polo"),
    db:               Session    = Depends(get_db),
):
    q = db.query(models.Empresa)

    # si me filtran por tipo de servicio, hago el join y filtro por ServicioPolo.tipo
    if tipo_servicio:
        q = (
            q
            .join(models.Empresa.servicios_polo)
            .join(models.EmpresaServicioPolo.servicio_polo)
            .filter(models.ServicioPolo.tipo.ilike(f"%{tipo_servicio}%"))
        )

    if nombre:
        q = q.filter(models.Empresa.nombre.ilike(f"%{nombre}%"))
    if rubro:
        q = q.filter(models.Empresa.rubro.ilike(f"%{rubro}%"))

    empresas = q.all()
    result: list[schemas.CompanyFullOut] = []

    for emp in empresas:
        vehs = [schemas.VehiculoOut.from_orm(v) for v in emp.vehiculos]
        conts = [schemas.ContactoOut.from_orm(c) for c in emp.contactos]

        servs = []
        for esp in emp.servicios_polo:
            svc = esp.servicio_polo
            lotes = [schemas.LoteOut.from_orm(l) for l in svc.lotes]
            servs.append(
                schemas.ServicioPoloOut(
                    id_servicio_polo=svc.id_servicio_polo,
                    nombre=svc.nombre,
                    tipo=svc.tipo,
                    horario=svc.horario,
                    datos=svc.datos,
                    lotes=lotes
                )
            )

        result.append(
            schemas.CompanyFullOut(
                nombre=emp.nombre,
                rubro=emp.rubro,
                observaciones=emp.observaciones,
                horario_trabajo=emp.horario_trabajo,
                vehiculos=vehs,
                contactos=conts,
                servicios_polo=servs,
            )
        )

    return result



@router.get(
    "/companies_all",
    response_model=list[schemas.CompanyFullOut],
    summary="Listar empresas con todos sus datos relacionados"
)
def list_companies_full(db: Session = Depends(get_db)):
    emps = db.query(models.Empresa).all()
    result: list[schemas.CompanyFullOut] = []

    for emp in emps:
        # Vehículos
        vehs = [schemas.VehiculoOut.from_orm(v) for v in emp.vehiculos]
        # Contactos
        conts = [schemas.ContactoOut.from_orm(c) for c in emp.contactos]
        # Servicios del Polo + sus lotes
        servs = []
        for esp in emp.servicios_polo:
            svc = esp.servicio_polo
            lotes = [schemas.LoteOut.from_orm(l) for l in svc.lotes]
            # construyo el output a mano para inyectar los lotes
            out_svc = schemas.ServicioPoloOut(
                id_servicio_polo=svc.id_servicio_polo,
                nombre=svc.nombre,
                tipo=svc.tipo,
                horario=svc.horario,
                datos=svc.datos,
                lotes=lotes
            )
            servs.append(out_svc)

        result.append(
            schemas.CompanyFullOut(
                nombre=emp.nombre,
                rubro=emp.rubro,
                observaciones=emp.observaciones,
                horario_trabajo=emp.horario_trabajo,
                vehiculos=vehs,
                contactos=conts,
                servicios_polo=servs,
            )
        )

    return result
