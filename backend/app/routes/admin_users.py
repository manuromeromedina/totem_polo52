#app/routes/admin_users.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import date
from uuid import UUID
from typing import List
from app.config import SessionLocal
from app import models, schemas, services
from app.models import Empresa, ServicioPolo, TipoServicioPolo, Rol
from app.schemas import (
    EmpresaOut, EmpresaCreate, RolOut, EmpresaDetailOutPublic, 
    ContactoOutPublic, LoteOutPublic
)
from app.routes.auth import require_admin_polo, get_current_user

router = APIRouter(
    prefix="",
    tags=["Admin_polo"],
    dependencies=[Depends(require_admin_polo)],
)

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y CONSTANTES
# ═══════════════════════════════════════════════════════════════════

# Constante para identificar al polo - AJUSTAR SEGÚN TU LÓGICA
POLO_CUIL = 44123456789  # Reemplaza con el CUIL real del polo en tu BD

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def build_empresa_detail_public(emp: models.Empresa) -> schemas.EmpresaDetailOutPublic:
    """Construir detalle público de empresa con contactos y servicios polo"""
    # Contactos
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

    # Servicios asociados al Polo
    servicios_polo = []
    for esp in emp.servicios_polo:
        svc = esp
        tipo_servicio_polo = svc.tipo_servicio.tipo if svc.tipo_servicio else None
        # Lotes asociados al servicio del polo
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

    return schemas.EmpresaDetailOutPublic(
        nombre=emp.nombre,
        rubro=emp.rubro,
        fecha_ingreso=emp.fecha_ingreso,
        horario_trabajo=emp.horario_trabajo,
        contactos=conts,
        servicios_polo=servicios_polo
    )

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

@router.post("/polo/change-password-request", summary="Solicitar cambio de contraseña para admin polo")
def polo_change_password_request(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envía un email con enlace para cambiar la contraseña del admin polo"""
    # Usar la lógica del endpoint existente en auth.py
    token = services.create_password_reset_token(current_user.email)
    reset_link = f"http://localhost:4200/password-reset?token={token}"
    
    # Enviar email (reutilizar lógica de auth.py)
    try:
        from email.mime.text import MIMEText
        import smtplib
        from app.config import settings
        
        email_body = f"""
Hola {current_user.nombre},

Has solicitado cambiar tu contraseña como administrador del polo.

Para proceder con el cambio, haz clic en el siguiente enlace:
{reset_link}

RECUERDA:
• Necesitarás tu contraseña actual
• Deberás confirmar la nueva contraseña dos veces
• No podrás reutilizar contraseñas anteriores
• Este enlace expira en 1 hora

Si no solicitaste este cambio, ignora este email.

Saludos,
Sistema Polo 52
        """
        
        msg = MIMEText(email_body)
        msg["Subject"] = "Cambio de Contraseña Admin Polo - Polo 52"
        msg["From"] = settings.EMAIL_USER
        msg["To"] = current_user.email
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.send_message(msg)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando email: {str(e)}")
    
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
    # Verificar que no exista el usuario
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre")
    
    if db.query(models.Usuario).filter(models.Usuario.email == dto.email).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
    
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
# GESTIÓN DE EMPRESAS
# ═══════════════════════════════════════════════════════════════════

@router.post("/empresas", response_model=EmpresaOut, summary="Crear una nueva empresa")
def create_empresa(dto: EmpresaCreate, db: Session = Depends(get_db)):
    """Crear nueva empresa en el sistema"""
    if db.query(Empresa).filter(Empresa.cuil == dto.cuil).first():
        raise HTTPException(status_code=400, detail="Ya existe una empresa con ese CUIL")

    nueva = Empresa(
        cuil=dto.cuil,
        nombre=dto.nombre,
        rubro=dto.rubro,
        cant_empleados=dto.cant_empleados,
        observaciones=dto.observaciones,
        fecha_ingreso=dto.fecha_ingreso or date.today(),
        horario_trabajo=dto.horario_trabajo
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

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

    db.commit()
    db.refresh(emp)
    return emp

@router.delete("/empresas/{cuil}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una empresa")
def delete_empresa(cuil: int, db: Session = Depends(get_db)):
    """Eliminar empresa del sistema (elimina cascada relacionados)"""
    empresa = db.query(Empresa).filter(Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(empresa)
    db.commit()

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
    """Crear nuevo lote y asociarlo a un servicio de polo"""
    lote = models.Lote(
        dueno=dto.dueno,
        lote=dto.lote,
        manzana=dto.manzana,
        id_servicio_polo=dto.id_servicio_polo,
    )
    db.add(lote)
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

# ═══════════════════════════════════════════════════════════════════
# BÚSQUEDAS Y CONSULTAS PÚBLICAS
# ═══════════════════════════════════════════════════════════════════

@router.get("/all", response_model=List[EmpresaDetailOutPublic], summary="Obtener todas las empresas con detalles completos")
def get_all_companies(db: Session = Depends(get_db)):
    """Listar todas las empresas con información detallada para consulta pública"""
    empresas = db.query(Empresa).all()
    if not empresas:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")
    
    empresa_details = []
    for empresa in empresas:
        empresa_details.append(build_empresa_detail_public(empresa))
    
    return empresa_details

@router.get("/search", response_model=List[EmpresaDetailOutPublic], summary="Buscar empresas por criterios específicos")
def search_companies(
    name: str = None,
    rubro: str = None,
    servicio_polo: str = None,
    db: Session = Depends(get_db)
):
    """Buscar empresas por nombre, rubro o tipo de servicio del polo"""
    query = db.query(Empresa)
    
    # Filtrar por nombre
    if name:
        query = query.filter(Empresa.nombre.ilike(f"%{name}%"))
    
    # Filtrar por rubro
    if rubro:
        query = query.filter(Empresa.rubro.ilike(f"%{rubro}%"))
    
    # Filtrar por tipo de servicio_polo
    if servicio_polo:
        query = query.join(ServicioPolo).join(TipoServicioPolo).filter(
            TipoServicioPolo.tipo.ilike(f"%{servicio_polo}%")
        )

    companies = query.all()

    if not companies:
        raise HTTPException(status_code=404, detail="No se encontraron empresas")
    
    empresa_details = []
    for empresa in companies:
        empresa_details.append(build_empresa_detail_public(empresa))
    
    return empresa_details

@router.get("/search/contactos", response_model=List[ContactoOutPublic], summary="Buscar contactos por empresa")
def search_companies_contacts(name: str = None, db: Session = Depends(get_db)):
    """Buscar empresas por nombre y devolver solo los contactos"""
    query = db.query(Empresa)
    
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
def search_companies_lotes(name: str = None, db: Session = Depends(get_db)):
    """Buscar empresas por nombre y devolver solo los lotes"""
    query = db.query(Empresa)
    
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