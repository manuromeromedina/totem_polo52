from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app.main import get_current_user, require_empresa_role
from app import models, schemas

router = APIRouter(
    prefix="",               # OJO: sin "/companies" aquí
    tags=["empresa"],
    dependencies=[Depends(require_empresa_role)],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def build_empresa_detail(emp: models.Empresa) -> schemas.EmpresaDetailOut:
    vehs = [schemas.VehiculoOut.from_orm(v) for v in emp.vehiculos]
    conts = [schemas.ContactoOut.from_orm(c) for c in emp.contactos]
    servicios = []
    for esp in emp.servicios_polo:
        svc = esp.servicio_polo
        lotes = [schemas.LoteOut.from_orm(l) for l in svc.lotes]
        servicios.append(
            schemas.ServicioPoloOut(
                id_servicio_polo=svc.id_servicio_polo,
                nombre=svc.nombre,
                tipo=svc.tipo,
                horario=svc.horario,
                datos=svc.datos,
                lotes=lotes
            )
        )
    return schemas.EmpresaDetailOut(
        cuil=emp.cuil,
        nombre=emp.nombre,
        rubro=emp.rubro,
        cant_empleados=emp.cant_empleados,
        observaciones=emp.observaciones,
        fecha_ingreso=emp.fecha_ingreso,
        horario_trabajo=emp.horario_trabajo,
        vehiculos=vehs,
        contactos=conts,
        servicios_polo=servicios
    )

@router.get(
    "/me",
    response_model=schemas.EmpresaDetailOut,
    summary="Mis datos completos de empresa"
)
def read_me(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                   = Depends(get_db),
):
    emp = db.query(models.Empresa).filter_by(cuil=current_user.cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")
    return build_empresa_detail(emp)

@router.put(
    "/companies/{cuil}",
    response_model=schemas.EmpresaDetailOut,
    summary="Actualizar todos los datos de mi empresa (menos cuil/fecha_ingreso)"
)
def full_update_company(
    cuil: int,
    dto: schemas.EmpresaDetailUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                   = Depends(get_db),
):
    if current_user.cuil != cuil:
        raise HTTPException(403, "No puedes editar otra empresa")
    emp = db.query(models.Empresa).filter_by(cuil=cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")

    data = dto.model_dump(exclude_unset=True)

    # — Actualizo campos directos de Empresa —
    for f in ("nombre", "rubro", "cant_empleados", "observaciones", "horario_trabajo"):
        if f in data:
            setattr(emp, f, data[f])

    # — Upsert vehículos —
    if data.get("vehiculos") is not None:
        for v in data["vehiculos"]:
            vid = v.get("id_vehiculo")
            if vid:
                obj = db.query(models.Vehiculo).filter_by(id_vehiculo=vid, cuil=cuil).first()
                if not obj:
                    raise HTTPException(404, f"Vehículo {vid} no existe")
                for f2 in ("tipo", "horarios", "frecuencia", "datos"):
                    if v.get(f2) is not None:
                        setattr(obj, f2, v[f2])
            else:
                db.add(models.Vehiculo(
                    cuil=cuil,
                    tipo=v.get("tipo"),
                    horarios=v.get("horarios"),
                    frecuencia=v.get("frecuencia"),
                    datos=v.get("datos")
                ))

    # — Upsert contactos —
    if data.get("contactos") is not None:
        for c in data["contactos"]:
            cid = c.get("id_contacto")
            if cid:
                obj = db.query(models.Contacto).filter_by(id_contacto=cid, cuil_empresa=cuil).first()
                if not obj:
                    raise HTTPException(404, f"Contacto {cid} no existe")
                for f2 in ("tipo", "nombre", "telefono", "datos", "direccion", "id_servicio_polo"):
                    if c.get(f2) is not None:
                        setattr(obj, f2, c[f2])
            else:
                db.add(models.Contacto(
                    cuil_empresa=cuil,
                    tipo=c.get("tipo"),
                    nombre=c.get("nombre"),
                    telefono=c.get("telefono"),
                    datos=c.get("datos"),
                    direccion=c.get("direccion"),
                    id_servicio_polo=c.get("id_servicio_polo")
                ))

    # — Upsert servicios_polo + lotes —
    if data.get("servicios_polo") is not None:
        for s in data["servicios_polo"]:
            sid = s.get("id_servicio_polo")
            if not db.query(models.EmpresaServicioPolo).filter_by(cuil=cuil, id_servicio_polo=sid).first():
                db.add(models.EmpresaServicioPolo(cuil=cuil, id_servicio_polo=sid))
            svc = db.get(models.ServicioPolo, sid)
            if not svc:
                raise HTTPException(404, f"Servicio Polo {sid} no existe")
            for f2 in ("nombre", "tipo", "horario", "datos"):
                if s.get(f2) is not None:
                    setattr(svc, f2, s[f2])
            if s.get("lotes") is not None:
                for l in s["lotes"]:
                    lid = l.get("id_lote")
                    if lid:
                        lo = db.query(models.Lote).filter_by(id_lote=lid, id_servicio_polo=sid).first()
                        if not lo:
                            raise HTTPException(404, f"Lote {lid} no existe")
                        for f2 in ("dueno", "lote", "manzana"):
                            if l.get(f2) is not None:
                                setattr(lo, f2, l[f2])
                    else:
                        db.add(models.Lote(
                            id_servicio_polo=sid,
                            dueno=l.get("dueno"),
                            lote=l.get("lote"),
                            manzana=l.get("manzana")
                        ))

    db.commit()
    db.refresh(emp)
    return build_empresa_detail(emp)
