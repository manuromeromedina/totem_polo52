#company_user.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app.routes.auth import get_current_user, require_empresa_role
from app import models, schemas, services

router = APIRouter(
    prefix="",
    tags=["Admin_empresa"],
)

def get_db():
    db = SessionLocal() 
    try: 
        yield db
    finally: 
        db.close()

# ─── Actualizar contraseña del usuario ───────────────────────────────────────

@router.put("/update_password", response_model=schemas.UserOut, summary="Actualizar la contraseña del usuario")
def update_password(
    dto: schemas.UserUpdateCompany,  # Recibimos los datos a actualizar
    current_user: models.Usuario = Depends(get_current_user),  # Obtenemos al usuario logueado
    db: Session = Depends(get_db)
):
    # Verificamos si la contraseña fue proporcionada
    if dto.password is None:
        raise HTTPException(status_code=400, detail="Se debe proporcionar una nueva contraseña")

    # Recuperamos el usuario logueado
    user = db.query(models.Usuario).filter(models.Usuario.id_usuario == current_user.id_usuario).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Actualizamos la contraseña del usuario
    user.contrasena = services.hash_password(dto.password)  # Hasheamos la nueva contraseña
    db.commit()
    db.refresh(user)  # Refrescamos al usuario para reflejar los cambios

    return user


# ─── Vehiculos ────────────────────────────────────────────────────────

@router.post("/vehiculos", response_model=schemas.VehiculoOut, summary="Crear un vehículo")
def create_vehiculo(
    dto: schemas.VehiculoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        print(f"🚗 Datos recibidos: {dto.model_dump()}")
        print(f"👤 Usuario: {current_user.nombre}, CUIL: {current_user.cuil}")
        
        # Verificar que el tipo de vehículo existe
        tipo_vehiculo = db.query(models.TipoVehiculo).filter(
            models.TipoVehiculo.id_tipo_vehiculo == dto.id_tipo_vehiculo
        ).first()
        
        if not tipo_vehiculo:
            print(f"❌ Tipo de vehículo {dto.id_tipo_vehiculo} no existe")
            raise HTTPException(status_code=400, detail=f"Tipo de vehículo {dto.id_tipo_vehiculo} no existe")
        validar_datos_vehiculo(dto, tipo_vehiculo)

        
        print(f"✅ Tipo de vehículo encontrado: {tipo_vehiculo.tipo}")
        
        v = models.Vehiculo(
            id_tipo_vehiculo=dto.id_tipo_vehiculo,
            horarios=dto.horarios,
            frecuencia=dto.frecuencia,
            datos=dto.datos,
        )
        db.add(v)
        db.flush()  # para obtener v.id_vehiculo
        
        print(f"✅ Vehículo creado con ID: {v.id_vehiculo}")

        # Verificar que la empresa existe
        empresa = db.query(models.Empresa).filter(models.Empresa.cuil == current_user.cuil).first()
        if not empresa:
            print(f"❌ Empresa con CUIL {current_user.cuil} no existe")
            raise HTTPException(status_code=400, detail=f"Empresa con CUIL {current_user.cuil} no existe")
        
        print(f"✅ Empresa encontrada: {empresa.nombre}")

        link = models.VehiculosEmpresa(
            id_vehiculo=v.id_vehiculo,
            cuil=current_user.cuil,
        )
        db.add(link)
        db.commit()
        db.refresh(v)
        
        print(f"✅ Link creado exitosamente")
        return v
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en create_vehiculo: {str(e)}")
        print(f"❌ Tipo de error: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/vehiculos/{veh_id}", response_model=schemas.VehiculoOut, summary="Actualizar un vehículo")
def update_vehiculo(
    veh_id: int,
    dto: schemas.VehiculoCreate,
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
    
    # Corregir este loop
    for f in ("horarios", "frecuencia", "datos", "id_tipo_vehiculo"):  # Cambia "id_tipo_vehiculos" por "id_tipo_vehiculo"
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
    vehs = []
    for v in emp.vehiculos_emp:
        veh = v.vehiculo
        tipo_vehiculo = veh.tipo_vehiculo.tipo if veh.tipo_vehiculo else None  # Obtener el tipo de vehículo
        vehs.append(
            schemas.VehiculoOut(
                id_vehiculo=veh.id_vehiculo,
                id_tipo_vehiculo=veh.id_tipo_vehiculo,
                horarios=veh.horarios,
                frecuencia=veh.frecuencia,
                datos=veh.datos,
                tipo_vehiculo=tipo_vehiculo  # Incluir el tipo de vehículo
            )
        )

    conts = []
    for c in emp.contactos:
        tipo_contacto = c.tipo_contacto.tipo if c.tipo_contacto else None  # Obtener el tipo de contacto
        conts.append(
            schemas.ContactoOut(
                id_contacto=c.id_contacto,
                id_tipo_contacto=c.id_tipo_contacto,
                nombre=c.nombre,
                telefono=c.telefono,
                datos=c.datos,
                direccion=c.direccion,
                id_servicio_polo=c.id_servicio_polo,
                tipo_contacto=tipo_contacto  # Incluir el tipo de contacto
            )
        )

    # Servicios propios de la empresa (servicios que no están asociados a servicios del polo)
    servicios = []
    for esp in emp.servicios:
        svc = esp.servicio  # Servicios que no están asociados al polo
        tipo_servicio = svc.tipo_servicio.tipo if svc.tipo_servicio else None  # Obtener el tipo de servicio
        servicios.append(
            schemas.ServicioOut(
                id_servicio=svc.id_servicio,
                datos=svc.datos,
                id_tipo_servicio=svc.id_tipo_servicio,
                tipo_servicio=tipo_servicio  # Incluir el tipo de servicio
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
            schemas.ServicioPoloOut(
                id_servicio_polo=svc.id_servicio_polo,
                nombre=svc.nombre,
                horario=svc.horario,
                datos=svc.datos,
                propietario=svc.propietario,
                id_tipo_servicio_polo=svc.id_tipo_servicio_polo,
                cuil=svc.cuil,
                tipo_servicio_polo=tipo_servicio_polo,  # Incluir el tipo de servicio del Polo
                lotes=lotes  # Incluir los lotes relacionados
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




# Agregar al final de company_user.py
@router.get("/tipos/vehiculo", response_model=list[schemas.TipoVehiculoOut], summary="Obtener tipos de vehículo")
def get_tipos_vehiculo(db: Session = Depends(get_db)):
    return db.query(models.TipoVehiculo).all()

@router.get("/tipos/servicio", response_model=list[schemas.TipoServicioOut], summary="Obtener tipos de servicio")
def get_tipos_servicio(db: Session = Depends(get_db)):  # CAMBIA EL NOMBRE AQUÍ
    return db.query(models.TipoServicio).all()

@router.get("/tipos/contacto", response_model=list[schemas.TipoContactoOut], summary="Obtener tipos de contacto")
def get_tipos_contacto(db: Session = Depends(get_db)):  # CAMBIA EL NOMBRE AQUÍ
    return db.query(models.TipoContacto).all()


def validar_datos_vehiculo(dto: schemas.VehiculoCreate, tipo_vehiculo: models.TipoVehiculo):
    datos = dto.datos

    if tipo_vehiculo.id_tipo_vehiculo == 1:  # Corporativo
        if not all(k in datos for k in ("cantidad", "patente", "carga")):
            raise HTTPException(status_code=400, detail="Para vehículos corporativos, los datos deben incluir cantidad, patente y carga")
        if datos.get("carga") not in ("baja", "mediana", "alta"):
            raise HTTPException(status_code=400, detail="El valor de 'carga' debe ser 'baja', 'mediana' o 'alta'")

    elif tipo_vehiculo.id_tipo_vehiculo == 2:  # Personal
        if not all(k in datos for k in ("cantidad", "patente")):
            raise HTTPException(status_code=400, detail="Para vehículos personales, los datos deben incluir cantidad y patente")

    elif tipo_vehiculo.id_tipo_vehiculo == 3:  # Terceros
        if not all(k in datos for k in ("cantidad", "carga")):
            raise HTTPException(status_code=400, detail="Para vehículos de terceros, los datos deben incluir cantidad y carga")
        if datos.get("carga") not in ("baja", "mediana", "alta"):
            raise HTTPException(status_code=400, detail="El valor de 'carga' debe ser 'baja', 'mediana' o 'alta'")
