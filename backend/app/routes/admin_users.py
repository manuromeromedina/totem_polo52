#admin_users.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import date
from uuid import UUID
from app.config import SessionLocal
from app import models, schemas, services
import uuid
from app.models import Empresa
from app.schemas import EmpresaOut, EmpresaCreate

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Usuarios ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[schemas.UserOut], summary="Listar usuarios")
def list_users(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()

@router.get("/{user_id}", response_model=schemas.UserOut, summary="Ver usuario")
def get_user(user_id: UUID, db: Session = Depends(get_db)):  
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    return u

@router.post(
    "/usuarios",
    response_model=schemas.UserOut,
    summary="Crear un nuevo usuario y asignarle un rol"
)
def create_user(
    dto: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese nombre")

    new_user = models.Usuario(
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

@router.put("/usuarios/{user_id}", response_model=schemas.UserOut, summary="Actualizar usuario")
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


@router.delete("/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Inhabilitar usuario")
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
    summary="Crear una nueva empresa"
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
    summary="[admin_polo] Actualizar sólo nombre y rubro de una empresa"
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
    summary="Eliminar una empresa"
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
    summary="Crear un servicio de polo"
)
def create_servicio_polo(
    dto: schemas.ServicioPoloUpdate,  # Usamos el esquema que necesites para crear el servicio
    db: Session = Depends(get_db),
):
    servicio = models.ServicioPolo(
        nombre=dto.nombre,
        horario=dto.horario,
        datos=dto.datos,
        propietario=dto.propietario,
        id_tipo_servicio_polo=dto.id_tipo_servicio_polo
    )
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio

@router.put("/serviciopolo/{id_servicio_polo}",
    response_model=schemas.ServicioPoloOut,
    summary="Actualizar un servicio de polo"
)
def update_servicio_polo(
    id_servicio_polo: int,
    dto: schemas.ServicioPoloUpdate,
    db: Session = Depends(get_db),
):
    servicio = db.query(models.ServicioPolo).filter(models.ServicioPolo.id_servicio_polo == id_servicio_polo).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio del polo no encontrado")
    
    for field, value in dto.dict().items():
        if value is not None:
            setattr(servicio, field, value)
    
    db.commit()
    db.refresh(servicio)
    return servicio

@router.delete("/serviciopolo/{id_servicio_polo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un servicio de polo"
)
def delete_servicio_polo(
    id_servicio_polo: int,
    db: Session = Depends(get_db),
):
    servicio = db.query(models.ServicioPolo).filter(models.ServicioPolo.id_servicio_polo == id_servicio_polo).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio del polo no encontrado")
    
    db.delete(servicio)
    db.commit()
    return {"msg": "Servicio del polo eliminado exitosamente"}

@router.post("/empresas/{cuil}/serviciopolo/{id_servicio_polo}", 
             response_model=schemas.EmpresaServicioPoloAssign, 
             summary="Asociar empresa con un servicio polo")
def assign_servicio_polo_to_empresa(
    cuil: int,
    id_servicio_polo: int,
    db: Session = Depends(get_db),
):
    # Verificar si la empresa existe
    empresa = db.query(models.Empresa).filter_by(cuil=cuil).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Verificar si el servicio de polo existe
    servicio_polo = db.query(models.ServicioPolo).filter_by(id_servicio_polo=id_servicio_polo).first()
    if not servicio_polo:
        raise HTTPException(status_code=404, detail="Servicio de Polo no encontrado")

    # Verificar si la asociación ya existe
    if db.query(models.EmpresaServicioPolo).filter_by(cuil=cuil, id_servicio_polo=id_servicio_polo).first():
        raise HTTPException(status_code=400, detail="La empresa ya está asociada con este servicio de polo")

    # Crear la asociación
    empresa_servicio_polo = models.EmpresaServicioPolo(
        cuil=cuil,
        id_servicio_polo=id_servicio_polo,
    )
    
    db.add(empresa_servicio_polo)
    db.commit()
    db.refresh(empresa_servicio_polo)
    return empresa_servicio_polo

@router.delete("/empresas/{cuil}/serviciopolo/{id_servicio_polo}",
               status_code=status.HTTP_204_NO_CONTENT, 
               summary="Desasociar empresa de un servicio polo")
def remove_servicio_polo_from_empresa(
    cuil: int,
    id_servicio_polo: int,
    db: Session = Depends(get_db),
):
    # Verificar si la asociación existe
    empresa_servicio_polo = db.query(models.EmpresaServicioPolo).filter_by(cuil=cuil, id_servicio_polo=id_servicio_polo).first()
    if not empresa_servicio_polo:
        raise HTTPException(status_code=404, detail="La empresa no está asociada a este servicio de polo")

    # Eliminar la asociación
    db.delete(empresa_servicio_polo)
    db.commit()
    return {"msg": "Asociación eliminada exitosamente"}

