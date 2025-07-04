#admin_users.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import date
from uuid import UUID
from app.config import SessionLocal
from app import models, schemas, services
from app.models import Empresa
from app.schemas import EmpresaOut, EmpresaCreate, RolOut
from typing import List
from app.models import Rol
from app.routes.auth import require_admin_polo  # Importamos la validación de roles desde auth.py

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
    summary="Crear un nuevo usuario y asignarle un rol",
    dependencies=[Depends(require_admin_polo)]  # Se requiere el rol admin_polo
)
def create_user(
    dto: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre")

    new_user = models.Usuario(
        email         = dto.email,
        nombre        = dto.nombre,
        contrasena    = services.hash_password(dto.password),
        estado        = dto.estado,
        fecha_registro= date.today(),
        cuil          = dto.cuil,
    )
    db.add(new_user)
    db.flush()

    rol = db.query(models.Rol).filter(models.Rol.id_rol == dto.id_rol).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol inválido")

    enlace = models.RolUsuario(
        id_usuario=new_user.id_usuario,
        id_rol    = rol.id_rol
    )
    db.add(enlace)

    db.commit()
    db.refresh(new_user)
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

