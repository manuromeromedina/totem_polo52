#app/routes/admin_users.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import date
from uuid import UUID
from app.config import SessionLocal
from app import models, schemas, services
from app.models import Empresa, ServicioPolo, TipoServicioPolo
from app.schemas import EmpresaOut, EmpresaCreate, RolOut, EmpresaDetailOutPublic, ContactoOutPublic, LoteOutPublic
from typing import List
from app.models import Rol
from app.routes.auth import require_admin_polo, get_current_user  # Importamos la validación de roles desde auth.py# Importamos la validación de roles desde auth.py

router = APIRouter(
    prefix="",
    tags=["Admin_polo"],
    dependencies=[Depends(require_admin_polo)],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




# Constante para identificar al polo - AJUSTAR SEGÚN TU LÓGICA
POLO_CUIL = 44123456789  # Reemplaza con el CUIL real del polo en tu BD

@router.get("/polo/me", 
    response_model=schemas.PoloDetailOut, 
    summary="Obtener información completa del polo",
    dependencies=[Depends(require_admin_polo)]
)
def get_polo_details(
    db: Session = Depends(get_db),
):
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


@router.put("/polo/me",
    response_model=schemas.PoloDetailOut,
    summary="Actualizar datos del polo",
    dependencies=[Depends(require_admin_polo)]
)
def update_polo_details(
    dto: schemas.PoloSelfUpdate,
    db: Session = Depends(get_db),
):
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


@router.post("/polo/change-password-request",
    summary="Solicitar cambio de contraseña para admin polo",
    dependencies=[Depends(require_admin_polo)]
)
def polo_change_password_request(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Envía un email con enlace para cambiar la contraseña del admin polo.
    """
    # Aquí implementas la misma lógica que tienes en auth.py
    # para generar token y enviar email
    
    # Por ahora retornamos un mensaje de éxito
    return {
        "message": "Se ha enviado un enlace de cambio de contraseña a tu email",
        "email": current_user.email
    }


# Agregar estos endpoints en admin_users.py

@router.get("/empresas", response_model=List[EmpresaOut], summary="Listar todas las empresas")
def list_empresas(db: Session = Depends(get_db)):
    """
    Devuelve todas las empresas registradas en el sistema.
    """
    return db.query(models.Empresa).all()

@router.get("/usuarios", response_model=List[schemas.UserOut], summary="Listar todos los usuarios")
def list_usuarios(db: Session = Depends(get_db)):
    """
    Devuelve todos los usuarios registrados en el sistema.
    """
    return db.query(models.Usuario).all()

@router.get("/serviciopolo", response_model=List[schemas.ServicioPoloOut], summary="Listar servicios del polo")
def list_servicios_polo(db: Session = Depends(get_db)):
    """
    Devuelve todos los servicios del polo registrados.
    """
    return db.query(models.ServicioPolo).all()

@router.get("/lotes", response_model=List[schemas.LoteOut], summary="Listar todos los lotes")
def list_lotes(db: Session = Depends(get_db)):
    """
    Devuelve todos los lotes registrados.
    """
    return db.query(models.Lote).all()


# ─── Usuarios ─────────────────────────────────────────────────────────────────

@router.get(
    "/roles",
    response_model=List[RolOut],
    summary="Listar roles disponibles",
    dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def list_roles(db: Session = Depends(get_db)):
    """
    Devuelve todos los roles que existen en la tabla `rol`.
    """
    return db.query(Rol).all()

@router.get("/{user_id}", response_model=schemas.UserOut, summary="Ver usuario", dependencies=[Depends(require_admin_polo)])  
def get_user(user_id: UUID, db: Session = Depends(get_db)):  
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    return u

@router.post(
    "/usuarios",
    response_model=schemas.UserOut,
    summary="Crear un nuevo usuario con contraseña automática",
    dependencies=[Depends(require_admin_polo)]
)
def create_user(
    dto: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    # Verificar que no exista el usuario
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre")
    
    if db.query(models.Usuario).filter(models.Usuario.email == dto.email).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
    
    # Verificar que el rol existe
    rol = db.query(models.Rol).filter(models.Rol.id_rol == dto.id_rol).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol inválido")
    
    # GENERAR CONTRASEÑA AUTOMÁTICA
    generated_password = services.generate_random_password()
    hashed_password = services.hash_password(generated_password)
    
    # Crear el usuario
    new_user = models.Usuario(
        email         = dto.email,
        nombre        = dto.nombre,
        contrasena    = hashed_password,  # Usar la contraseña hasheada
        estado        = dto.estado,
        fecha_registro= date.today(),
        cuil          = dto.cuil,
    )
    db.add(new_user)
    db.flush()

    # Crear la relación rol-usuario
    enlace = models.RolUsuario(
        id_usuario=new_user.id_usuario,
        id_rol    = rol.id_rol
    )
    db.add(enlace)
    
    # Hacer commit para asegurar que el usuario se guarde
    db.commit()
    db.refresh(new_user)
    
    # ENVIAR EMAIL CON CREDENCIALES
    email_sent = services.send_welcome_email(
        email=dto.email,
        nombre=dto.nombre,
        username=dto.nombre,  # o dto.email si prefieres login por email
        password=generated_password  # Contraseña sin hashear para el email
    )
    
    if not email_sent:
        # Si no se pudo enviar el email, podrías decidir:
        # 1. Fallar completamente (rollback)
        # 2. Continuar pero notificar al admin
        # 3. Guardar la contraseña para mostrarla en la respuesta
        
        # Opción 2: Continuar pero advertir
        print(f" Usuario creado pero email no enviado para: {dto.email}")
    
    return new_user


@router.put("/usuarios/{user_id}", response_model=schemas.UserOut, summary="Actualizar usuario", dependencies=[Depends(require_admin_polo)])  
def update_user(user_id: UUID, dto: schemas.UserUpdate, db: Session = Depends(get_db)):  # Usamos UUID
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    if dto.password:
        u.contrasena = services.hash_password(dto.password)
    if dto.estado is not None:  # Actualizamos el estado si es necesario
        u.estado = dto.estado
    db.commit()
    db.refresh(u)
    return u


@router.delete("/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Inhabilitar usuario", dependencies=[Depends(require_admin_polo)])  
def delete_user(user_id: UUID, db: Session = Depends(get_db)):  # Usamos UUID
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    
    u.estado = False  # Marcamos como inhabilitado
    db.commit()
    return {"msg": "Usuario inhabilitado exitosamente"}



# ─── Empresas (sólo atributos básicos) ────────────────────────────────────────

@router.post(
    "/empresas",
    response_model=EmpresaOut,
    summary="Crear una nueva empresa",
    dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def create_empresa(
    dto: EmpresaCreate,
    db: Session = Depends(get_db),
):
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

@router.put(
    "/empresas/{cuil}",
    response_model=schemas.EmpresaOut,
    summary="[admin_polo] Actualizar sólo nombre y rubro de una empresa",
    dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def admin_update_empresa_nombre_rubro(
    cuil: int,
    dto: schemas.EmpresaAdminUpdate,  # <- nuevo schema con solo nombre y rubro
    db: Session = Depends(get_db),
):
    emp = db.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Actualizamos únicamente los campos permitidos
    if dto.nombre is not None:
        emp.nombre = dto.nombre
    if dto.rubro is not None:
        emp.rubro = dto.rubro

    db.commit()
    db.refresh(emp)
    return emp

@router.delete(
    "/empresas/{cuil}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una empresa",
    dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def delete_empresa(
    cuil: int,
    db: Session = Depends(get_db),
):
    empresa = db.query(Empresa).filter(Empresa.cuil == cuil).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(empresa)
    db.commit()


# ─── Servicio del Polo ─────────────────────────────────────────────────

@router.post("/serviciopolo",
    response_model=schemas.ServicioPoloOut,
    summary="Crear un servicio de polo",
    dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def create_servicio_polo(
    dto: schemas.ServicioPoloCreate,  # Usamos el esquema actualizado
    db: Session = Depends(get_db),
):
    servicio = models.ServicioPolo(
        nombre=dto.nombre,
        horario=dto.horario,
        datos=dto.datos,
        propietario=dto.propietario,
        id_tipo_servicio_polo=dto.id_tipo_servicio_polo,
        cuil=dto.cuil  # Asociamos el servicio con la empresa mediante el cuil
    )
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio

@router.delete("/serviciopolo/{id_servicio_polo}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar un servicio de polo",
               dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def delete_servicio_polo(
    id_servicio_polo: int,
    db: Session = Depends(get_db),
):
    # Verificamos si el servicio existe
    servicio = db.query(models.ServicioPolo).filter(models.ServicioPolo.id_servicio_polo == id_servicio_polo).first()
    
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio del polo no encontrado")
    
    # Eliminamos los lotes relacionados si es necesario (esto depende del comportamiento que se desee)
    for lote in servicio.lotes:
        db.delete(lote)

    # Finalmente, eliminamos el servicio
    db.delete(servicio)
    db.commit()
    
    return {"msg": "Servicio del polo eliminado exitosamente"}


@router.post("/lotes",
    response_model=schemas.LoteOut,
    summary="Crear un lote y asociarlo a un servicio de polo",
    dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def create_lote(
    dto: schemas.LoteCreate,
    db: Session = Depends(get_db),
):
    lote = models.Lote(
        dueno=dto.dueno,
        lote=dto.lote,
        manzana=dto.manzana,
        id_servicio_polo=dto.id_servicio_polo,  # Asociamos el lote con el servicio de polo
    )
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote

@router.delete("/lotes/{id_lotes}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar un lote",
               dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def delete_lote(
    id_lotes: int,
    db: Session = Depends(get_db),
):
    # Verificamos si el lote existe
    lote = db.query(models.Lote).filter(models.Lote.id_lotes == id_lotes).first()
    
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    # Eliminamos el lote
    db.delete(lote)
    db.commit()
    
    return {"msg": "Lote eliminado exitosamente"}

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