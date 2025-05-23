#company_user.py
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
    db = SessionLocal() 
    try: 
        yield db
    finally: 
        db.close()

# ─── Vehiculos ────────────────────────────────────────────────────────
@router.post("/vehiculos", response_model=schemas.VehiculoOut, summary="Crear un vehículo")
def create_vehiculo(
    dto: schemas.VehiculoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    v = models.Vehiculo(
        id_tipo_vehiculo=dto.id_tipo_vehiculo,
        horarios=dto.horarios,
        frecuencia=dto.frecuencia,
        datos=dto.datos,
    )
    db.add(v)
    db.flush()  # para obtener v.id_vehiculo

    link = models.VehiculosEmpresa(
        id_vehiculo=v.id_vehiculo,
        cuil=current_user.cuil,
    )
    db.add(link)
    db.commit()
    db.refresh(v)
    return v



@router.put("/vehiculos/{veh_id}", response_model=schemas.VehiculoOut, summary="Actualizar un vehículo")
def update_vehiculo(
    veh_id: int,
    dto: schemas.VehiculoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Consulta con join para filtrar vehículos relacionados con el cuil del usuario
    v = (
        db.query(models.Vehiculo)
        .join(models.VehiculosEmpresa)
        .filter(
            models.Vehiculo.id_vehiculo == veh_id,
            models.VehiculosEmpresa.cuil == current_user.cuil,
        )
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no existe")
    for f in ("horarios", "frecuencia", "datos", "id_tipo_vehiculos"):
        val = getattr(dto, f, None)
        if val is not None:
            setattr(v, f, val)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/vehiculos/{veh_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un vehículo")
def delete_vehiculo(
    veh_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    v = (
        db.query(models.Vehiculo)
        .join(models.VehiculosEmpresa)
        .filter(
            models.Vehiculo.id_vehiculo == veh_id,
            models.VehiculosEmpresa.cuil == current_user.cuil,
        )
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no existe")
    db.delete(v)
    db.commit()

# ─── Servicios ────────────────────────────────────────────────────────
@router.post("/servicios", response_model=schemas.ServicioOut, summary="Crear un servicio")
def create_servicio(
    dto: schemas.ServicioCreate,  # DTO para la creación de servicio
    current_user: models.Usuario = Depends(get_current_user),  # Obtener el usuario actual
    db: Session = Depends(get_db)
):
    # Creamos el servicio
    servicio = models.Servicio(
        datos=dto.datos,  # Datos adicionales en formato JSON
        id_tipo_servicio=dto.id_tipo_servicio
    )
    db.add(servicio)
    db.commit()
    db.refresh(servicio)

    # Asociamos el servicio con la empresa del usuario autenticado (admin_empresa)
    empresa_servicio = models.EmpresaServicio(
        cuil=current_user.cuil,  # Obtenemos el cuil del usuario autenticado
        id_servicio=servicio.id_servicio,
    )
    db.add(empresa_servicio)
    db.commit()
    db.refresh(empresa_servicio)

    return servicio


@router.put("/servicios/{servicio_id}", response_model=schemas.ServicioOut, summary="Actualizar un servicio")
def update_servicio(
    servicio_id: int,
    dto: schemas.ServicioUpdate,  # DTO para actualizar servicio
    db: Session = Depends(get_db)
):
    servicio = db.query(models.Servicio).filter(models.Servicio.id_servicio == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    for field, value in dto.model_dump(exclude_unset=True).items():  # Actualiza solo los campos no vacíos
        setattr(servicio, field, value)

    db.commit()
    db.refresh(servicio)
    return servicio

@router.delete("/servicios/{servicio_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un servicio")
def delete_servicio(
    servicio_id: int,
    db: Session = Depends(get_db)
):
    servicio = db.query(models.Servicio).filter(models.Servicio.id_servicio == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    db.delete(servicio)
    db.commit()
    return {"msg": "Servicio eliminado correctamente"}


# ─── Contacto ────────────────────────────────────────────────────────
@router.post("/contactos",
    response_model=schemas.ContactoOut,
    summary="Crear un contacto para la empresa"
)
def create_contacto(
    dto: schemas.ContactoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contacto = models.Contacto(
        cuil_empresa=current_user.cuil,
        id_tipo_contacto=dto.id_tipo_contacto,
        nombre=dto.nombre,
        telefono=dto.telefono,
        datos=dto.datos,
        direccion=dto.direccion,
        id_servicio_polo=dto.id_servicio_polo,
    )
    db.add(contacto)
    db.commit()
    db.refresh(contacto)
    return contacto


@router.put("/contactos/{cid}",
    response_model=schemas.ContactoOut,
    summary="Actualizar un contacto para la empresa"
)
def update_contacto(
    cid: int,
    dto: schemas.ContactoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contacto = db.query(models.Contacto).filter_by(id_contacto=cid, cuil_empresa=current_user.cuil).first()
    if not contacto:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    for field, value in dto.dict().items():
        if value is not None:
            setattr(contacto, field, value)
    
    db.commit()
    db.refresh(contacto)
    return contacto


@router.delete("/contactos/{cid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un contacto para la empresa"
)
def delete_contacto(
    cid: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contacto = db.query(models.Contacto).filter_by(id_contacto=cid, cuil_empresa=current_user.cuil).first()
    if not contacto:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    db.delete(contacto)
    db.commit()
    return {"msg": "Contacto eliminado exitosamente"}



# ─── Datos de mi empresa ────────────────────────────────────────────────────────
@router.put(
    "/companies/me",
    response_model=schemas.EmpresaSelfOut,
    summary="Actualizar mis datos de empresa (cant_empleados, observaciones, horario_trabajo)"
)
def update_my_company(
    dto: schemas.EmpresaSelfUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # El cuil ya está disponible en current_user, no es necesario pasarlo en la URL
    cuil = current_user.cuil

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
    # Creamos las listas para cada relación de la empresa
    vehs = [schemas.VehiculoOut.from_orm(v.vehiculo) for v in emp.vehiculos_emp]
    conts = [schemas.ContactoOut.from_orm(c) for c in emp.contactos]

    # Servicios propios de la empresa (servicios que no están asociados a servicios del polo)
    servicios = []
    for esp in emp.servicios:
        svc = esp.servicio
        servicios.append(
            schemas.ServicioOut(
                id_servicio=svc.id_servicio,
                datos=svc.datos,
                id_tipo_servicio=svc.id_tipo_servicio
            )
        )

    # Servicios asociados al Polo (asegurarse de que siempre haya una lista, incluso vacía)
    servicios_polo = []
    for esp in emp.servicios_polo:
        svc = esp.servicio_polo
        lotes = [schemas.LoteOut.from_orm(l) for l in svc.lotes]  # Lotes asociados al servicio
        servicios_polo.append(
            schemas.ServicioPoloOut(
                id_servicio_polo=svc.id_servicio_polo,
                nombre=svc.nombre,
                tipo=svc.tipo_servicio.tipo,  # Aseguramos que se incluya el tipo del servicio
                horario=svc.horario,
                datos=svc.datos,
                lotes=lotes
            )
        )

    # Ahora armamos y devolvemos el objeto con los detalles completos de la empresa
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
        servicios=servicios,
        servicios_polo=servicios_polo  # Siempre pasa una lista, aunque esté vacía
    )


@router.get("/me", response_model=schemas.EmpresaDetailOut, summary="Mis datos completos de empresa")
def read_me(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = db.query(models.Empresa).filter_by(cuil=current_user.cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")
    return build_empresa_detail(emp)

