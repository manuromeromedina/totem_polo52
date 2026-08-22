#app/routes/admin_users.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session, joinedload
from datetime import date
from uuid import UUID
from typing import List
import os
from app.config import get_db
from app import models, schemas, services
from app.models import Empresa, Rol
from app.schemas import EmpresaOut, RolOut
from app.routes.auth import require_admin_polo, get_current_user
import re
NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]+$")

router = APIRouter(
    prefix="",
    tags=["Admin_polo"],
    dependencies=[Depends(require_admin_polo)],
)

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y CONSTANTES
# ═══════════════════════════════════════════════════════════════════

# CUIL de la empresa que representa al propio Polo 52 en la tabla `empresa`.
# Configurable por env var porque es un dato real de la organización, no una
# constante de código. El default coincide con el placeholder que crea el
# bootstrap inicial (ver app/bootstrap.py) para que /polo/me encuentre esa
# empresa desde el primer arranque; reemplazalo por el CUIL real cuando lo
# tengas y actualizá el registro existente en la tabla `empresa`.
POLO_CUIL = int(os.getenv("POLO_CUIL", "44123456789"))

# Límites de usuarios por tipo de rol
MAX_ADMIN_EMPRESA_PER_COMPANY = 3
MAX_ADMIN_POLO_TOTAL = 3
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:4200").rstrip("/")

def _count_active_users_by_role(db: Session, tipo_rol: str, cuil: int = None) -> int:
    """Cuenta usuarios activos con un rol dado, opcionalmente filtrando por empresa."""
    query = (
        db.query(models.Usuario)
        .join(models.RolUsuario)
        .join(models.Rol)
        .filter(models.Rol.tipo_rol == tipo_rol)
        .filter(models.Usuario.estado == True)
    )
    if cuil is not None:
        query = query.filter(models.Usuario.cuil == cuil)
    return query.count()


def validate_user_creation_limits(db: Session, dto: schemas.UserCreate):
    """Validar límites de creación de usuarios según el rol y empresa"""
    
    # Obtener información del rol
    rol = db.query(models.Rol).filter(models.Rol.id_rol == dto.id_rol).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol inválido")
    
    # Validación para admin_polo
    if rol.tipo_rol == "admin_polo":
        # Verificar que la empresa sea el POLO
        if dto.cuil != POLO_CUIL:
            raise HTTPException(
                status_code=400, 
                detail="El rol admin_polo solo puede asignarse a usuarios de la empresa Polo"
            )
        
        # Contar admin_polo existentes
        admin_polo_count = _count_active_users_by_role(db, "admin_polo")

        if admin_polo_count >= MAX_ADMIN_POLO_TOTAL:
            raise HTTPException(
                status_code=400,
                detail=f"No se pueden crear más de {MAX_ADMIN_POLO_TOTAL} usuarios admin_polo. "
                       f"Actualmente hay {admin_polo_count}. Si necesita más usuarios, "
                       f"contacte con soporte técnico."
            )
    
    # admin_empresa ya no se crea a mano: se crea (junto con su empresa) por
    # el autoregistro público (POST /register) y su posterior aprobación por
    # admin_polo (POST /empresas/{cuil}/aprobar).
    elif rol.tipo_rol == "admin_empresa":
        raise HTTPException(
            status_code=400,
            detail="Los usuarios admin_empresa se crean mediante el registro público "
                   "de la empresa y su aprobación por admin_polo, no desde acá."
        )

    # Validación para usuarios públicos
    elif rol.tipo_rol == "publico":
        # Verificar que SOLO se puedan crear en la empresa Polo
        if dto.cuil != POLO_CUIL:
            raise HTTPException(
                status_code=400,
                detail="Los usuarios con rol 'publico' solo pueden crearse en la empresa Polo. "
                       "Las demás empresas solo pueden tener usuarios 'admin_empresa'."
            )

def validate_user_activation_limits(db: Session, user: models.Usuario):
    """Validar límites específicamente para rehabilitar/activar usuarios existentes"""
    
    # Obtener el rol del usuario
    if not user.rol_usuario_links:
        raise HTTPException(status_code=400, detail="Usuario sin rol asignado")
    
    rol_id = user.rol_usuario_links[0].id_rol
    rol = db.query(models.Rol).filter(models.Rol.id_rol == rol_id).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol del usuario inválido")
    
    # Validación para admin_polo
    if rol.tipo_rol == "admin_polo":
        admin_polo_count = _count_active_users_by_role(db, "admin_polo")

        if admin_polo_count >= MAX_ADMIN_POLO_TOTAL:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede activar este usuario admin_polo. "
                       f"Ya hay {admin_polo_count} usuarios admin_polo activos (máximo: {MAX_ADMIN_POLO_TOTAL}). "
                       f"Debe inhabilitar otro usuario admin_polo antes de activar este."
            )
    
    # Validación para admin_empresa
    elif rol.tipo_rol == "admin_empresa":
        admin_empresa_count = _count_active_users_by_role(db, "admin_empresa", cuil=user.cuil)

        if admin_empresa_count >= MAX_ADMIN_EMPRESA_PER_COMPANY:
            empresa = db.query(models.Empresa).filter(models.Empresa.cuil == user.cuil).first()
            empresa_nombre = empresa.nombre if empresa else f"CUIL {user.cuil}"
            
            raise HTTPException(
                status_code=400,
                detail=f"No se puede activar este usuario admin_empresa. "
                       f"La empresa '{empresa_nombre}' ya tiene {admin_empresa_count} usuarios activos "
                       f"(máximo: {MAX_ADMIN_EMPRESA_PER_COMPANY}). "
                       f"Debe inhabilitar otro usuario admin_empresa de esta empresa antes de activar este."
            )
    
    # Para usuarios públicos no hay límite, siempre se permite activar

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DEL POLO
# ═══════════════════════════════════════════════════════════════════

@router.get("/polo/me", 
    response_model=schemas.PoloDetailOut, 
    summary="Obtener información completa del polo"
)
def get_polo_details(db: Session = Depends(get_db)):
    """
    Devuelve la información completa del polo incluyendo:
    - Datos básicos del polo (empresa con CUIL específico)
    - Lista de todas las empresas registradas (excluyendo al polo)
    - Lista de todos los servicios del polo
    - Lista de todos los usuarios
    - Lista de todos los lotes
    """
    # Obtener los datos del polo (empresa específica)
    polo_empresa = db.query(models.Empresa).filter(models.Empresa.cuil == POLO_CUIL).first()
    
    if not polo_empresa:
        raise HTTPException(status_code=404, detail="Polo no encontrado")
    
    # Obtener todas las empresas EXCEPTO el polo
    empresas = db.query(models.Empresa).filter(models.Empresa.cuil != POLO_CUIL).all()
    
    # Obtener todos los servicios del polo
    servicios_polo = db.query(models.ServicioPolo).all()
    
    # Obtener todos los usuarios
    usuarios = db.query(models.Usuario).all()
    
    # Obtener todos los lotes
    lotes = db.query(models.Lote).all()
    
    return schemas.PoloDetailOut(
        # Datos del polo
        cuil=polo_empresa.cuil,
        nombre=polo_empresa.nombre,
        rubro=polo_empresa.rubro,
        cant_empleados=polo_empresa.cant_empleados,
        fecha_ingreso=polo_empresa.fecha_ingreso,
        horario_trabajo=polo_empresa.horario_trabajo,
        observaciones=polo_empresa.observaciones,
        
        # Listas de entidades gestionadas
        empresas=[schemas.EmpresaOut.from_orm(e) for e in empresas],
        servicios_polo=[schemas.ServicioPoloOut.from_orm(s) for s in servicios_polo],
        usuarios=[schemas.UserOut.from_orm(u) for u in usuarios],
        lotes=[schemas.LoteOut.from_orm(l) for l in lotes]
    )

@router.put("/polo/me", response_model=schemas.PoloDetailOut, summary="Actualizar datos del polo")
def update_polo_details(dto: schemas.PoloSelfUpdate, db: Session = Depends(get_db)):
    """
    Actualiza los datos editables del polo:
    - cant_empleados
    - horario_trabajo  
    - observaciones
    """
    polo_empresa = db.query(models.Empresa).filter(models.Empresa.cuil == POLO_CUIL).first()
    
    if not polo_empresa:
        raise HTTPException(status_code=404, detail="Polo no encontrado")
    
    # Actualizar solo los campos permitidos
    data = dto.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(polo_empresa, field, value)
    
    db.commit()
    db.refresh(polo_empresa)
    
    # Devolver la información completa actualizada
    return get_polo_details(db)

# ═══════════════════════════════════════════════════════════════════
# INFORMACIÓN COMERCIAL DEL POLO (misma ficha que usan las empresas,
# pero para la propia empresa Polo, solo accesible por admin_polo)
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/polo/comercial",
    response_model=schemas.InfoComercialOut,
    summary="Ver la información comercial cargada del Polo",
)
def read_polo_comercial_info(db: Session = Depends(get_db)):
    """Obtener la ficha comercial cargada (o parcialmente cargada) del Polo"""
    row = db.query(models.InfoComercial).filter_by(cuil=POLO_CUIL).first()
    if not row:
        raise HTTPException(status_code=404, detail="Todavía no se cargó información comercial del Polo")
    return row


@router.put(
    "/polo/comercial",
    response_model=schemas.InfoComercialOut,
    summary="Cargar/editar la información comercial del Polo",
)
def update_polo_comercial_info(dto: schemas.InfoComercialUpdate, db: Session = Depends(get_db)):
    """
    Crea o actualiza la ficha comercial del Polo directamente (sin wizard):
    la carga un admin_polo con datos ya conocidos, no se completa de a un
    campo por vez como en el flujo de las empresas.
    """
    row = db.query(models.InfoComercial).filter_by(cuil=POLO_CUIL).first()
    if not row:
        row = models.InfoComercial(cuil=POLO_CUIL)
        db.add(row)

    data = dto.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(row, field, value)
    row.completado = True
    row.fecha_actualizacion = date.today()

    db.commit()
    db.refresh(row)
    return row

@router.post("/polo/change-password-request", summary="Solicitar cambio de contraseña para admin polo")
def polo_change_password_request(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envía un email con enlace para cambiar la contraseña del admin polo"""
    token = services.create_password_reset_token(current_user.email)
    reset_link = f"{FRONTEND_BASE_URL}/password-reset?token={token}"

    sent = services.send_admin_password_change_request_email(
        email=current_user.email,
        nombre=current_user.nombre,
        reset_link=reset_link,
    )
    if not sent:
        raise HTTPException(status_code=500, detail="Error enviando email")

    return {
        "message": "Se ha enviado un enlace de cambio de contraseña a tu email",
        "email": f"{current_user.email[:3]}***@{current_user.email.split('@')[1]}"
    }

# ═══════════════════════════════════════════════════════════════════
# LISTADOS GENERALES
# ═══════════════════════════════════════════════════════════════════

@router.get("/empresas", response_model=List[EmpresaOut], summary="Listar todas las empresas")
def list_empresas(db: Session = Depends(get_db)):
    """Devuelve todas las empresas registradas en el sistema"""
    return db.query(models.Empresa).all()

@router.get("/usuarios", response_model=List[schemas.UserOut], summary="Listar todos los usuarios")
def list_usuarios(db: Session = Depends(get_db)):
    """Devuelve todos los usuarios registrados en el sistema"""
    return db.query(models.Usuario).all()

@router.get("/serviciopolo", response_model=List[schemas.ServicioPoloOut], summary="Listar servicios del polo")
def list_servicios_polo(db: Session = Depends(get_db)):
    """Devuelve todos los servicios del polo registrados"""
    return db.query(models.ServicioPolo).all()

@router.get("/lotes", response_model=List[schemas.LoteOut], summary="Listar todos los lotes")
def list_lotes(db: Session = Depends(get_db)):
    """Devuelve todos los lotes registrados"""
    return db.query(models.Lote).all()

@router.get("/roles", response_model=List[RolOut], summary="Listar roles disponibles")
def list_roles(db: Session = Depends(get_db)):
    """Devuelve todos los roles que existen en la tabla rol"""
    return db.query(Rol).all()

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE USUARIOS
# ═══════════════════════════════════════════════════════════════════

@router.get("/usuarios/{user_id}", response_model=schemas.UserOut, summary="Ver usuario específico")
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """Obtener información de un usuario específico"""
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    return u

@router.post("/usuarios", response_model=schemas.UserOut, summary="Crear un nuevo usuario con contraseña automática")
def create_user(dto: schemas.UserCreate, db: Session = Depends(get_db)):
    """Crear nuevo usuario con contraseña generada automáticamente"""
    
    # VALIDACIÓN: Verificar límites antes de crear
    validate_user_creation_limits(db, dto)
    
    # Verificar que no exista el usuario
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre")
    
    if db.query(models.Usuario).filter(models.Usuario.email == dto.email).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
    
    # Verificar que la empresa existe
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == dto.cuil).first()
    if not empresa:
        raise HTTPException(
            status_code=400, 
            detail=f"No existe una empresa registrada con CUIL {dto.cuil}"
        )
    
    # Verificar que el rol existe
    rol = db.query(models.Rol).filter(models.Rol.id_rol == dto.id_rol).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol inválido")
    
    # Generar contraseña automática
    generated_password = services.generate_random_password()
    hashed_password = services.hash_password(generated_password)
    
    # Crear el usuario
    new_user = models.Usuario(
        email=dto.email,
        nombre=dto.nombre,
        contrasena=hashed_password,
        estado=dto.estado,
        fecha_registro=date.today(),
        cuil=dto.cuil,
    )
    db.add(new_user)
    db.flush()

    # Crear la relación rol-usuario
    enlace = models.RolUsuario(
        id_usuario=new_user.id_usuario,
        id_rol=rol.id_rol
    )
    db.add(enlace)
    
    db.commit()
    db.refresh(new_user)
    
    # Enviar email con credenciales
    email_sent = services.send_welcome_email(
        email=dto.email,
        nombre=dto.nombre,
        username=dto.nombre,
        password=generated_password
    )
    
    if not email_sent:
        print(f"Usuario creado pero email no enviado para: {dto.email}")
    
    return new_user

@router.put("/usuarios/{user_id}", response_model=schemas.UserOut, summary="Actualizar usuario")
def update_user(user_id: UUID, dto: schemas.UserUpdate, db: Session = Depends(get_db)):
    """Actualizar información de usuario existente"""
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    
    # Si se está cambiando el estado de False a True (rehabilitando usuario)
    # VALIDAR LÍMITES ESTRICTOS - SIN EXCEPCIONES
    if dto.estado is not None and dto.estado == True and u.estado == False:
        validate_user_activation_limits(db, u)
    
    if dto.password:
        # Validar que no reutilice contraseñas anteriores
        if services.is_password_reused(db, u.id_usuario, dto.password):
            raise HTTPException(
                status_code=400, 
                detail="No puede usar una contraseña ya utilizada anteriormente"
            )
        
        # Guardar contraseña actual en historial
        services.save_password_to_history(db, u.id_usuario, u.contrasena)
        u.contrasena = services.hash_password(dto.password)
    
    if dto.estado is not None:
        u.estado = dto.estado
    
    db.commit()
    db.refresh(u)
    return u

@router.delete("/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Inhabilitar usuario")
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    """Inhabilitar usuario (no elimina físicamente)"""
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    
    u.estado = False  # Marcamos como inhabilitado
    db.commit()
    return {"msg": "Usuario inhabilitado exitosamente"}

# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS DE LÍMITES Y CONSULTAS
# ═══════════════════════════════════════════════════════════════════

@router.get("/usuarios/limits-status", summary="Consultar límites de usuarios por empresa")
def get_users_limits_status(db: Session = Depends(get_db)):
    """Obtener información sobre límites de usuarios y estado actual"""
    
    # Información del Polo
    polo_admin_count = _count_active_users_by_role(db, "admin_polo")

    # Contar usuarios públicos en el polo
    polo_public_count = _count_active_users_by_role(db, "publico", cuil=POLO_CUIL)

    # Información por empresa (admin_empresa)
    empresas_info = []
    empresas = db.query(models.Empresa).filter(models.Empresa.cuil != POLO_CUIL).all()

    for empresa in empresas:
        admin_count = _count_active_users_by_role(db, "admin_empresa", cuil=empresa.cuil)

        empresas_info.append({
            "cuil": empresa.cuil,
            "nombre": empresa.nombre,
            "admin_empresa_actuales": admin_count,
            "limite_admin_empresa": MAX_ADMIN_EMPRESA_PER_COMPANY,
            "puede_crear_mas": admin_count < MAX_ADMIN_EMPRESA_PER_COMPANY
        })
    
    return {
        "polo_info": {
            "admin_polo_actuales": polo_admin_count,
            "usuarios_publicos_actuales": polo_public_count,
            "limite_admin_polo": MAX_ADMIN_POLO_TOTAL,
            "puede_crear_admin_polo": polo_admin_count < MAX_ADMIN_POLO_TOTAL,
            "puede_crear_publico": True  # Sin límite para públicos
        },
        "empresas_info": empresas_info,
        "limites_configurados": {
            "max_admin_empresa_per_company": MAX_ADMIN_EMPRESA_PER_COMPANY,
            "max_admin_polo_total": MAX_ADMIN_POLO_TOTAL,
            "polo_cuil": POLO_CUIL
        }
    }

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE EMPRESAS
# ═══════════════════════════════════════════════════════════════════

@router.put("/empresas/{cuil}", response_model=schemas.EmpresaOut, summary="Actualizar nombre y rubro de empresa")
def admin_update_empresa_nombre_rubro(
    cuil: int,
    dto: schemas.EmpresaAdminUpdate,
    db: Session = Depends(get_db),
):
    """Actualizar solo nombre y rubro de una empresa (admin_polo únicamente)"""
    emp = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Actualizar únicamente los campos permitidos
    if dto.nombre is not None:
        emp.nombre = dto.nombre
    if dto.rubro is not None:
        emp.rubro = dto.rubro
    if dto.estado is not None:
        emp.estado = dto.estado
    if dto.cant_empleados is not None:
        emp.cant_empleados = dto.cant_empleados
    if dto.observaciones is not None:
        emp.observaciones = dto.observaciones
    if dto.horario_trabajo is not None:
        emp.horario_trabajo = dto.horario_trabajo

    db.commit()
    db.refresh(emp)
    return emp

def _set_empresa_and_related_estado(empresa: models.Empresa, estado: bool) -> None:
    """Propaga el estado (activo/inactivo) de una empresa a sus registros relacionados."""
    empresa.estado = estado
    for usuario in empresa.usuarios:
        usuario.estado = estado
    for servicio_polo in empresa.servicios_polo:
        if hasattr(servicio_polo, "estado"):
            servicio_polo.estado = estado
    for emp_serv in empresa.servicios:
        if hasattr(emp_serv, "estado"):
            emp_serv.estado = estado
    for contacto in empresa.contactos:
        if hasattr(contacto, "estado"):
            contacto.estado = estado
    for vehiculo in empresa.vehiculos_emp:
        if hasattr(vehiculo, "estado"):
            vehiculo.estado = estado


@router.put("/empresas/{cuil}/desactivar", summary="Desactivar una empresa y sus registros asociados")
def desactivar_empresa(cuil: int, db: Session = Depends(get_db)):
    """
    Desactiva una empresa (baja lógica) y todos sus registros relacionados:
    usuarios, servicios del polo, servicios, contactos y vehículos.
    """
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    _set_empresa_and_related_estado(empresa, False)
    db.commit()
    return {"message": f"Empresa '{empresa.nombre}' y sus registros relacionados fueron desactivados correctamente."}


@router.put("/empresas/{cuil}/activar", summary="Reactivar una empresa y sus registros asociados")
def activar_empresa(cuil: int, db: Session = Depends(get_db)):
    """
    Reactiva una empresa (vuelve a 'estado=True') y todos sus registros relacionados:
    usuarios, servicios del polo, servicios, contactos y vehículos.
    """
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    _set_empresa_and_related_estado(empresa, True)
    db.commit()
    return {"message": f"Empresa '{empresa.nombre}' y sus registros relacionados fueron reactivados correctamente."}


# ═══════════════════════════════════════════════════════════════════
# SOLICITUDES DE REGISTRO (autoregistro público, pendientes de aprobación)
# ═══════════════════════════════════════════════════════════════════

@router.get("/empresas/solicitudes", summary="Listar solicitudes de registro pendientes")
def list_solicitudes_registro(db: Session = Depends(get_db)):
    """Empresas autoregistradas que todavía no fueron aprobadas ni rechazadas."""
    empresas = (
        db.query(models.Empresa)
        .filter(models.Empresa.estado_solicitud == "pendiente")
        .all()
    )
    resultado = []
    for empresa in empresas:
        usuario = empresa.usuarios[0] if empresa.usuarios else None
        resultado.append({
            "cuil": empresa.cuil,
            "nombre": empresa.nombre,
            "rubro": empresa.rubro,
            "cant_empleados": empresa.cant_empleados,
            "horario_trabajo": empresa.horario_trabajo,
            "observaciones": empresa.observaciones,
            "fecha_ingreso": empresa.fecha_ingreso,
            "estado_solicitud": empresa.estado_solicitud,
            "usuario": {
                "nombre": usuario.nombre,
                "email": usuario.email,
            } if usuario else None,
        })
    return resultado


@router.post("/empresas/{cuil}/aprobar", summary="Aprobar una solicitud de registro")
def aprobar_solicitud_registro(cuil: int, db: Session = Depends(get_db)):
    """
    Aprueba una empresa autoregistrada: la activa (junto con su usuario) y
    le manda un email avisando que ya puede ingresar. También sirve para
    revertir un rechazo anterior.
    """
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    empresa.estado_solicitud = "aprobada"
    _set_empresa_and_related_estado(empresa, True)
    db.commit()

    for usuario in empresa.usuarios:
        services.send_registration_approved_email(
            email=usuario.email,
            nombre=usuario.nombre,
            nombre_empresa=empresa.nombre,
        )

    return {"message": f"Empresa '{empresa.nombre}' aprobada correctamente."}


@router.post("/empresas/{cuil}/rechazar", summary="Rechazar una solicitud de registro")
def rechazar_solicitud_registro(cuil: int, db: Session = Depends(get_db)):
    """
    Rechaza una empresa autoregistrada: no borra nada, solo marca
    estado_solicitud='rechazada' (la empresa sigue inactiva). Reversible
    desde /empresas/{cuil}/aprobar.
    """
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    empresa.estado_solicitud = "rechazada"
    db.commit()

    for usuario in empresa.usuarios:
        services.send_registration_rejected_email(
            email=usuario.email,
            nombre=usuario.nombre,
            nombre_empresa=empresa.nombre,
        )

    return {"message": f"Solicitud de '{empresa.nombre}' rechazada."}


# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE SERVICIOS DEL POLO
# ═══════════════════════════════════════════════════════════════════

@router.post("/serviciopolo", response_model=schemas.ServicioPoloOut, summary="Crear un servicio de polo")
def create_servicio_polo(dto: schemas.ServicioPoloCreate, db: Session = Depends(get_db)):
    """Crear nuevo servicio del polo asociado a una empresa"""
    servicio = models.ServicioPolo(
        nombre=dto.nombre,
        horario=dto.horario,
        datos=dto.datos,
        propietario=dto.propietario,
        id_tipo_servicio_polo=dto.id_tipo_servicio_polo,
        cuil=dto.cuil
    )
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio

@router.delete("/serviciopolo/{id_servicio_polo}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un servicio de polo")
def delete_servicio_polo(id_servicio_polo: int, db: Session = Depends(get_db)):
    """Eliminar servicio del polo y sus lotes asociados"""
    servicio = db.query(models.ServicioPolo).filter(models.ServicioPolo.id_servicio_polo == id_servicio_polo).first()
    
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio del polo no encontrado")
    
    # Eliminar lotes relacionados (se eliminarán automáticamente por cascade)
    db.delete(servicio)
    db.commit()
    
    return {"msg": "Servicio del polo eliminado exitosamente"}

# ═══════════════════════════════════════════════════════════════════
# GESTIÓN DE LOTES
# ═══════════════════════════════════════════════════════════════════

@router.post("/lotes", response_model=schemas.LoteOut, summary="Crear un lote asociado a un servicio de polo")
def create_lote(dto: schemas.LoteCreate, db: Session = Depends(get_db)):
    """
    Crear nuevo lote y asociarlo a un servicio de polo.
    No permite duplicar lotes con misma manzana y número de lote.
    """
    # 🔍 Verificar duplicado de manzana + lote
    existing_lote = (
        db.query(models.Lote)
        .filter(models.Lote.manzana == dto.manzana)
        .filter(models.Lote.lote == dto.lote)
        .first()
    )
    if existing_lote:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Ya existe un lote con número '{dto.lote}' en la manzana '{dto.manzana}'. "
                "No se pueden crear lotes duplicados."
            )
        )
    
    # defensa extra por si llega fuera del esquema
    if not NAME_RE.fullmatch(dto.dueno.strip()):
        raise HTTPException(
            status_code=400,
            detail="El campo 'dueno' solo admite letras y espacios (sin números ni símbolos)"
        )

    # normalización opcional
    dueno_norm = re.sub(r"\s+", " ", dto.dueno.strip()).title()


    # Crear nuevo lote
    lote = models.Lote(
        dueno=dto.dueno,
        lote=dto.lote,
        manzana=dto.manzana,
        id_servicio_polo=dto.id_servicio_polo,
        latitud=dto.latitud,
        longitud=dto.longitud,
    )
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote

@router.put("/lotes/{id_lotes}", response_model=schemas.LoteOut, summary="Actualizar un lote (p.ej. su ubicacion en Google Maps)")
def update_lote(id_lotes: int, dto: schemas.LoteUpdate, db: Session = Depends(get_db)):
    """Actualizar campos de un lote existente. Solo pisa los campos enviados."""
    lote = db.query(models.Lote).filter(models.Lote.id_lotes == id_lotes).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    data = dto.model_dump(exclude_unset=True)

    if "dueno" in data:
        if not NAME_RE.fullmatch(data["dueno"].strip()):
            raise HTTPException(
                status_code=400,
                detail="El campo 'dueno' solo admite letras y espacios (sin números ni símbolos)"
            )
        data["dueno"] = re.sub(r"\s+", " ", data["dueno"].strip()).title()

    if "manzana" in data or "lote" in data:
        nueva_manzana = data.get("manzana", lote.manzana)
        nuevo_lote = data.get("lote", lote.lote)
        existing_lote = (
            db.query(models.Lote)
            .filter(models.Lote.manzana == nueva_manzana)
            .filter(models.Lote.lote == nuevo_lote)
            .filter(models.Lote.id_lotes != id_lotes)
            .first()
        )
        if existing_lote:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Ya existe un lote con número '{nuevo_lote}' en la manzana '{nueva_manzana}'. "
                    "No se pueden crear lotes duplicados."
                )
            )

    for field, value in data.items():
        setattr(lote, field, value)

    db.commit()
    db.refresh(lote)
    return lote

@router.delete("/lotes/{id_lotes}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un lote")
def delete_lote(id_lotes: int, db: Session = Depends(get_db)):
    """Eliminar lote específico"""
    lote = db.query(models.Lote).filter(models.Lote.id_lotes == id_lotes).first()
    
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    db.delete(lote)
    db.commit()
    
    return {"msg": "Lote eliminado exitosamente"}

