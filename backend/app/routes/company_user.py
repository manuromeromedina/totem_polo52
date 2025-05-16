# app/routes/company_user.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app.main import get_current_user, require_empresa_role
from app import models, schemas

router = APIRouter(
    prefix="",
    tags=["empresa"],
    dependencies=[Depends(require_empresa_role)],
)

def get_db():
    db = SessionLocal(); 
    try: yield db
    finally: db.close()

# --- Vehículos ---
@router.post("/vehiculos", response_model=schemas.VehiculoOut, summary="Crear un vehículo")
def create_vehiculo(
    dto: schemas.VehiculoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    v = models.Vehiculo(
        cuil=current_user.cuil,
        tipo=dto.tipo,
        horarios=dto.horarios,
        frecuencia=dto.frecuencia,
        datos=dto.datos,
    )
    db.add(v); db.commit(); db.refresh(v)
    return v

@router.put("/vehiculos/{veh_id}", response_model=schemas.VehiculoOut, summary="Actualizar un vehículo")
def update_vehiculo(
    veh_id: int,
    dto: schemas.VehiculoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    v = db.query(models.Vehiculo).filter_by(id_vehiculo=veh_id, cuil=current_user.cuil).first()
    if not v: raise HTTPException(404, "Vehículo no existe")
    for f in ("tipo","horarios","frecuencia","datos"):
        val = getattr(dto, f)
        if val is not None: setattr(v, f, val)
    db.commit(); db.refresh(v)
    return v

@router.delete("/vehiculos/{veh_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un vehículo")
def delete_vehiculo(
    veh_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    v = db.query(models.Vehiculo).filter_by(id_vehiculo=veh_id, cuil=current_user.cuil).first()
    if not v: raise HTTPException(404, "Vehículo no existe")
    db.delete(v); db.commit()


# --- Contactos ---
@router.post("/contactos", response_model=schemas.ContactoOut, summary="Crear un contacto")
def create_contacto(
    dto: schemas.ContactoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = models.Contacto(
        cuil_empresa=current_user.cuil,
        tipo=dto.tipo,
        nombre=dto.nombre,
        telefono=dto.telefono,
        datos=dto.datos,
        direccion=dto.direccion,
        id_servicio_polo=dto.id_servicio_polo,
    )
    db.add(c); db.commit(); db.refresh(c)
    return c

@router.put("/contactos/{cid}", response_model=schemas.ContactoOut, summary="Actualizar un contacto")
def update_contacto(
    cid: int,
    dto: schemas.ContactoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(models.Contacto).filter_by(id_contacto=cid, cuil_empresa=current_user.cuil).first()
    if not c: raise HTTPException(404, "Contacto no existe")
    for f in ("tipo","nombre","telefono","datos","direccion","id_servicio_polo"):
        val = getattr(dto, f)
        if val is not None: setattr(c, f, val)
    db.commit(); db.refresh(c)
    return c

@router.delete("/contactos/{cid}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un contacto")
def delete_contacto(
    cid: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(models.Contacto).filter_by(id_contacto=cid, cuil_empresa=current_user.cuil).first()
    if not c: raise HTTPException(404, "Contacto no existe")
    db.delete(c); db.commit()


# --- Lotes en un ServicioPolo ---
@router.post("/polo-services/{sid}/lotes", response_model=schemas.LoteOut, summary="Crear lote")
def create_lote(
    sid: int,
    dto: schemas.LoteCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # primero verifica que la empresa tenga asignado ese servicio_polo
    link = db.query(models.EmpresaServicioPolo).filter_by(
        cuil=current_user.cuil, id_servicio_polo=sid
    ).first()
    if not link: raise HTTPException(404, "Servicio del Polo no asignado")
    l = models.Lote(
        id_servicio_polo=sid,
        dueno=dto.dueno,
        lote=dto.lote,
        manzana=dto.manzana
    )
    db.add(l); db.commit(); db.refresh(l)
    return l

@router.put("/lotes/{lid}", response_model=schemas.LoteOut, summary="Actualizar lote")
def update_lote(
    lid: int,
    dto: schemas.LoteCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    l = db.query(models.Lote).join(models.ServicioPolo).join(models.EmpresaServicioPolo)\
         .filter(models.Lote.id_lotes==lid, models.EmpresaServicioPolo.cuil==current_user.cuil).first()
    if not l: raise HTTPException(404, "Lote no existe")
    for f in ("dueno","lote","manzana"):
        val = getattr(dto, f)
        if val is not None: setattr(l, f, val)
    db.commit(); db.refresh(l)
    return l

@router.delete("/lotes/{lid}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar lote")
def delete_lote(
    lid: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    l = db.query(models.Lote).join(models.ServicioPolo).join(models.EmpresaServicioPolo)\
         .filter(models.Lote.id_lotes==lid, models.EmpresaServicioPolo.cuil==current_user.cuil).first()
    if not l: raise HTTPException(404, "Lote no existe")
    db.delete(l); db.commit()


# --- Asignar/Quitar ServicioPolo ---
@router.post("/polo-services/{sid}", status_code=201, summary="Asignar servicio del Polo")
def assign_polo_service(
    sid: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not db.query(models.ServicioPolo).get(sid):
        raise HTTPException(404, "Servicio Polo no existe")
    link = models.EmpresaServicioPolo(cuil=current_user.cuil, id_servicio_polo=sid)
    db.add(link); db.commit()

@router.delete("/polo-services/{sid}", status_code=204, summary="Quitar servicio del Polo")
def unassign_polo_service(
    sid: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link = db.query(models.EmpresaServicioPolo)\
             .filter_by(cuil=current_user.cuil, id_servicio_polo=sid).first()
    if not link: raise HTTPException(404, "No estaba asignado")
    db.delete(link); db.commit()


# --- Asignar/Quitar Servicio propio de la Empresa ---
@router.post("/services", response_model=schemas.ServicioOut, summary="Asignar un servicio propio")
def assign_service(
    dto: schemas.ServiceCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = models.Servicio(nombre=dto.nombre, descripcion=dto.descripcion,
                         ubicacion=dto.ubicacion, disponibilidad=dto.disponibilidad,
                         horarios=dto.horarios)
    db.add(svc); db.flush()
    link = models.EmpresaServicio(cuil=current_user.cuil, id_servicio=svc.id_servicio)
    db.add(link); db.commit(); db.refresh(svc)
    return svc

@router.delete("/services/{sid}", status_code=204, summary="Quitar servicio propio")
def unassign_service(
    sid: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link = db.query(models.EmpresaServicio)\
             .filter_by(cuil=current_user.cuil, id_servicio=sid).first()
    if not link: raise HTTPException(404, "No estaba asignado")
    db.delete(link); db.commit()


@router.put(
    "/companies/{cuil}",
    response_model=schemas.EmpresaSelfOut,
    summary="Actualizar mis datos de empresa (cant_empleados, observaciones, horario_trabajo)"
)
def update_my_company(
    cuil: int,
    dto: schemas.EmpresaSelfUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session                   = Depends(get_db),
):
    # Sólo puedo editar mi propia empresa
    if current_user.cuil != cuil:
        raise HTTPException(403, "No puedes editar otra empresa")

    emp = db.query(models.Empresa).filter_by(cuil=cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")

    data = dto.model_dump(exclude_unset=True)

    # Actualizo sólo los campos permitidos
    for field, value in data.items():
        setattr(emp, field, value)

    db.commit()
    db.refresh(emp)

    # Como response_model=EmpresaSelfOut, FastAPI sólo serializa
    # cant_empleados, observaciones y horario_trabajo
    return emp


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