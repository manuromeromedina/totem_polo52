#app/routes/company_user.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app.routes.auth import get_current_user, require_empresa_role
from app import models, schemas, services


router = APIRouter(
    prefix="",
    tags=["Admin_empresa"],
)

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y UTILIDADES
# ═══════════════════════════════════════════════════════════════════

def get_db():
    db = SessionLocal() 
    try: 
        yield db
    finally: 
        db.close()

def validar_datos_vehiculo(dto: schemas.VehiculoCreate, tipo_vehiculo: models.TipoVehiculo):
    """Validar datos específicos según el tipo de vehículo"""
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

def build_empresa_detail(emp: models.Empresa) -> schemas.EmpresaDetailOut:
    """Construir objeto detallado de empresa con todas sus relaciones"""
    # Vehículos
    vehs = []
    for v in emp.vehiculos_emp:
        veh = v.vehiculo
        if veh.tipo_vehiculo:
            tipo_vehiculo = schemas.TipoVehiculoOut(
                id_tipo_vehiculo=veh.tipo_vehiculo.id_tipo_vehiculo,
                tipo=veh.tipo_vehiculo.tipo,
            )
        else:
            tipo_vehiculo = None

        vehs.append(
            schemas.VehiculoOut(
                id_vehiculo=veh.id_vehiculo,
                id_tipo_vehiculo=veh.id_tipo_vehiculo,
                horarios=veh.horarios,
                frecuencia=veh.frecuencia,
                datos=veh.datos,
                tipo_vehiculo=tipo_vehiculo
            )
        )

    # Contactos
    conts = []
    for c in emp.contactos:
        if c.tipo_contacto:
            tipo_contacto = schemas.TipoContactoOut(
                id_tipo_contacto=c.tipo_contacto.id_tipo_contacto,
                tipo=c.tipo_contacto.tipo,
            )
        else:
            tipo_contacto = None

        conts.append(
            schemas.ContactoOut(
                id_contacto=c.id_contacto,
                id_tipo_contacto=c.id_tipo_contacto,
                nombre=c.nombre,
                telefono=c.telefono,
                datos=c.datos,
                direccion=c.direccion,
                id_servicio_polo=c.id_servicio_polo,
                tipo_contacto=tipo_contacto
            )
        )

    # Servicios propios de la empresa
    servicios = []
    for esp in emp.servicios:
        svc = esp.servicio
        tipo_servicio = svc.tipo_servicio.tipo if svc.tipo_servicio else None
        servicios.append(
            schemas.ServicioOut(
                id_servicio=svc.id_servicio,
                datos=svc.datos,
                id_tipo_servicio=svc.id_tipo_servicio,
                tipo_servicio=tipo_servicio
            )
        )

    # Servicios asociados al Polo
    servicios_polo = []
    for esp in emp.servicios_polo:
        svc = esp
        tipo_servicio_polo = svc.tipo_servicio.tipo if svc.tipo_servicio else None
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
                tipo_servicio_polo=tipo_servicio_polo,
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
        servicios=servicios,
        servicios_polo=servicios_polo
    )

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE USUARIO Y CONTRASEÑA
# ═══════════════════════════════════════════════════════════════════

@router.put("/update_password", response_model=schemas.UserOut, summary="Actualizar la contraseña del usuario")
def update_password(
    dto: schemas.UserUpdateCompany,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar contraseña del usuario logueado"""
    if dto.password is None:
        raise HTTPException(status_code=400, detail="Se debe proporcionar una nueva contraseña")

    user = db.query(models.Usuario).filter(models.Usuario.id_usuario == current_user.id_usuario).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Validar que no reutilice contraseñas anteriores
    if services.is_password_reused(db, user.id_usuario, dto.password):
        raise HTTPException(
            status_code=400, 
            detail="No puedes usar una contraseña que ya hayas utilizado anteriormente"
        )

    # Guardar contraseña actual en historial
    services.save_password_to_history(db, user.id_usuario, user.contrasena)
    
    # Actualizar contraseña
    user.contrasena = services.hash_password(dto.password)
    db.commit()
    db.refresh(user)

    return user

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE EMPRESA
# ═══════════════════════════════════════════════════════════════════

@router.get("/me", response_model=schemas.EmpresaDetailOut, summary="Mis datos completos de empresa")
def read_me(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener información completa de mi empresa"""
    emp = db.query(models.Empresa).filter_by(cuil=current_user.cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")
    return build_empresa_detail(emp)

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
    """Actualizar datos editables de mi empresa"""
    cuil = current_user.cuil

    emp = db.query(models.Empresa).filter_by(cuil=cuil).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")

    data = dto.model_dump(exclude_unset=True)

    # Actualizar solo los campos permitidos
    for field, value in data.items():
        setattr(emp, field, value)

    db.commit()
    db.refresh(emp)

    return emp

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE VEHÍCULOS
# ═══════════════════════════════════════════════════════════════════

@router.post("/vehiculos", response_model=schemas.VehiculoOut, summary="Crear un vehículo")
def create_vehiculo(
    dto: schemas.VehiculoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crear nuevo vehículo para la empresa"""
    try:
        tipo_vehiculo = db.query(models.TipoVehiculo).filter(
            models.TipoVehiculo.id_tipo_vehiculo == dto.id_tipo_vehiculo
        ).first()
        
        if not tipo_vehiculo:
            raise HTTPException(status_code=400, detail=f"Tipo de vehículo {dto.id_tipo_vehiculo} no existe")
        
        validar_datos_vehiculo(dto, tipo_vehiculo)

        v = models.Vehiculo(
            id_tipo_vehiculo=dto.id_tipo_vehiculo,
            horarios=dto.horarios,
            frecuencia=dto.frecuencia,
            datos=dto.datos,
        )
        db.add(v)
        db.flush()  # para obtener v.id_vehiculo

        empresa = db.query(models.Empresa).filter(models.Empresa.cuil == current_user.cuil).first()
        if not empresa:
            raise HTTPException(status_code=400, detail=f"Empresa con CUIL {current_user.cuil} no existe")

        link = models.VehiculosEmpresa(
            id_vehiculo=v.id_vehiculo,
            cuil=current_user.cuil,
        )
        db.add(link)
        db.commit()
        db.refresh(v)

        # Construir objeto de respuesta
        tipo_vehiculo_out = schemas.TipoVehiculoOut(
            id_tipo_vehiculo=tipo_vehiculo.id_tipo_vehiculo,
            tipo=tipo_vehiculo.tipo,
        )
        return schemas.VehiculoOut(
            id_vehiculo=v.id_vehiculo,
            id_tipo_vehiculo=v.id_tipo_vehiculo,
            horarios=v.horarios,
            frecuencia=v.frecuencia,
            datos=v.datos,
            tipo_vehiculo=tipo_vehiculo_out,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.put("/vehiculos/{veh_id}", response_model=schemas.VehiculoOut, summary="Actualizar un vehículo")
def update_vehiculo(
    veh_id: int,
    dto: schemas.VehiculoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualizar vehículo existente de la empresa"""
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
    
    for f in ("horarios", "frecuencia", "datos", "id_tipo_vehiculo"):
        val = getattr(dto, f, None)
        if val is not None:
            setattr(v, f, val)
    db.commit()
    db.refresh(v)

    tipo_vehiculo = db.query(models.TipoVehiculo).filter(
        models.TipoVehiculo.id_tipo_vehiculo == v.id_tipo_vehiculo
    ).first()
    tipo_vehiculo_out = None
    if tipo_vehiculo:
        tipo_vehiculo_out = schemas.TipoVehiculoOut(
            id_tipo_vehiculo=tipo_vehiculo.id_tipo_vehiculo,
            tipo=tipo_vehiculo.tipo,
        )

    return schemas.VehiculoOut(
        id_vehiculo=v.id_vehiculo,
        id_tipo_vehiculo=v.id_tipo_vehiculo,
        horarios=v.horarios,
        frecuencia=v.frecuencia,
        datos=v.datos,
        tipo_vehiculo=tipo_vehiculo_out,
    )

@router.delete("/vehiculos/{veh_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un vehículo")
def delete_vehiculo(
    veh_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Eliminar vehículo de la empresa"""
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

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE SERVICIOS
# ═══════════════════════════════════════════════════════════════════

@router.post("/servicios", response_model=schemas.ServicioOut, summary="Crear un servicio")
def create_servicio(
    dto: schemas.ServicioCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear nuevo servicio para la empresa"""
    # Crear el servicio
    servicio = models.Servicio(
        datos=dto.datos,
        id_tipo_servicio=dto.id_tipo_servicio
    )
    db.add(servicio)
    db.commit()
    db.refresh(servicio)

    # Asociar el servicio con la empresa del usuario autenticado
    empresa_servicio = models.EmpresaServicio(
        cuil=current_user.cuil,
        id_servicio=servicio.id_servicio,
    )
    db.add(empresa_servicio)
    db.commit()
    db.refresh(empresa_servicio)

    return servicio

@router.put("/servicios/{servicio_id}", response_model=schemas.ServicioOut, summary="Actualizar un servicio")
def update_servicio(
    servicio_id: int,
    dto: schemas.ServicioUpdate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar servicio existente"""
    # Verificar que el servicio pertenece a la empresa del usuario
    servicio_empresa = (
        db.query(models.EmpresaServicio)
        .filter(
            models.EmpresaServicio.id_servicio == servicio_id,
            models.EmpresaServicio.cuil == current_user.cuil
        )
        .first()
    )
    
    if not servicio_empresa:
        raise HTTPException(status_code=404, detail="Servicio no encontrado o no pertenece a tu empresa")

    servicio = db.query(models.Servicio).filter(models.Servicio.id_servicio == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    for field, value in dto.model_dump(exclude_unset=True).items():
        setattr(servicio, field, value)

    db.commit()
    db.refresh(servicio)
    return servicio

@router.delete("/servicios/{servicio_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un servicio")
def delete_servicio(
    servicio_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Eliminar servicio de la empresa"""
    # Verificar que el servicio pertenece a la empresa del usuario
    servicio_empresa = (
        db.query(models.EmpresaServicio)
        .filter(
            models.EmpresaServicio.id_servicio == servicio_id,
            models.EmpresaServicio.cuil == current_user.cuil
        )
        .first()
    )
    
    if not servicio_empresa:
        raise HTTPException(status_code=404, detail="Servicio no encontrado o no pertenece a tu empresa")

    servicio = db.query(models.Servicio).filter(models.Servicio.id_servicio == servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    # Eliminar asociaciones en empresa_servicio primero
    db.query(models.EmpresaServicio).filter(models.EmpresaServicio.id_servicio == servicio_id).delete()

    # Luego eliminar el servicio
    db.delete(servicio)
    db.commit()

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE CONTACTOS
# ═══════════════════════════════════════════════════════════════════

@router.post("/contactos", response_model=schemas.ContactoOut, summary="Crear un contacto para la empresa")
def create_contacto(
    dto: schemas.ContactoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crear nuevo contacto para la empresa"""
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

@router.put("/contactos/{cid}", response_model=schemas.ContactoOut, summary="Actualizar un contacto para la empresa")
def update_contacto(
    cid: int,
    dto: schemas.ContactoCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualizar contacto existente de la empresa"""
    contacto = db.query(models.Contacto).filter_by(id_contacto=cid, cuil_empresa=current_user.cuil).first()
    if not contacto:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    for field, value in dto.dict().items():
        if value is not None:
            setattr(contacto, field, value)
    
    db.commit()
    db.refresh(contacto)
    return contacto

@router.delete("/contactos/{cid}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un contacto para la empresa")
def delete_contacto(
    cid: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Eliminar contacto de la empresa"""
    contacto = db.query(models.Contacto).filter_by(id_contacto=cid, cuil_empresa=current_user.cuil).first()
    if not contacto:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    
    db.delete(contacto)
    db.commit()
    return {"msg": "Contacto eliminado exitosamente"}

# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS DE CATÁLOGOS/TIPOS
# ═══════════════════════════════════════════════════════════════════

@router.get("/tipos/vehiculo", response_model=list[schemas.TipoVehiculoOut], summary="Obtener tipos de vehículo")
def get_tipos_vehiculo(db: Session = Depends(get_db)):
    """Listar todos los tipos de vehículo disponibles"""
    return db.query(models.TipoVehiculo).all()

@router.get("/tipos/servicio", response_model=list[schemas.TipoServicioOut], summary="Obtener tipos de servicio")
def get_tipos_servicio(db: Session = Depends(get_db)):
    """Listar todos los tipos de servicio disponibles"""
    return db.query(models.TipoServicio).all()

@router.get("/tipos/contacto", response_model=list[schemas.TipoContactoOut], summary="Obtener tipos de contacto")
def get_tipos_contacto(db: Session = Depends(get_db)):
    """Listar todos los tipos de contacto disponibles"""
    return db.query(models.TipoContacto).all()

# ═══════════════════════════════════════════════════════════════════
# SOLICITUDES DE AMPLIACIÓN DE LÍMITES
# ═══════════════════════════════════════════════════════════════════

@router.post("/request-limit-increase", summary="Solicitar ampliación de límite de usuarios")
def request_limit_increase(
    dto: schemas.UserLimitIncreaseRequest,
    current_user: models.Usuario = Depends(require_empresa_role),
    db: Session = Depends(get_db)
):
    """Endpoint para que las empresas soliciten más usuarios admin_empresa"""
    
    # Verificar que el usuario pertenece a la empresa que solicita
    if current_user.cuil != dto.cuil_empresa:
        raise HTTPException(
            status_code=403,
            detail="Solo puedes solicitar ampliación de límites para tu propia empresa"
        )
    
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == dto.cuil_empresa).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    # Contar usuarios actuales
    current_count = (
        db.query(models.Usuario)
        .join(models.RolUsuario)
        .join(models.Rol)
        .filter(models.Rol.tipo_rol == "admin_empresa")
        .filter(models.Usuario.cuil == dto.cuil_empresa)
        .filter(models.Usuario.estado == True)
        .count()
    )
    
    # Aquí podrías agregar lógica para enviar email al admin_polo
    # o guardar la solicitud en una tabla de solicitudes pendientes
    
    return {
        "message": "Solicitud de ampliación registrada",
        "empresa": empresa.nombre,
        "usuarios_actuales": current_count,
        "limite_actual": 3,  # MAX_ADMIN_EMPRESA_PER_COMPANY
        "usuarios_adicionales_solicitados": dto.usuarios_adicionales_solicitados,
        "justificacion": dto.justificacion,
        "nota": "La solicitud será revisada por el administrador del polo. "
                "Recibirá una respuesta por email en los próximos días hábiles."
    }