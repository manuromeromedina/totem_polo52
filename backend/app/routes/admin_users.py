# app/routes/admin_users.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import date

from app.config import SessionLocal
from app import models, schemas, services

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
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    return u


@router.post(
    "/",
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


@router.put("/{user_id}", response_model=schemas.UserOut, summary="Actualizar usuario")
def update_user(user_id: int, dto: schemas.UserUpdate, db: Session = Depends(get_db)):
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    if dto.password:
        u.contrasena = services.hash_password(dto.password)
    if dto.estado:
        u.estado = dto.estado
    db.commit()
    db.refresh(u)
    return u


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar usuario")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    db.delete(u)
    db.commit()


# ─── Empresas (sólo atributos básicos) ────────────────────────────────────────

from app.models import Empresa
from app.schemas import EmpresaOut, EmpresaCreate

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
        cuil            = dto.cuil,
        nombre          = dto.nombre,
        rubro           = dto.rubro,
        cant_empleados  = dto.cant_empleados,
        observaciones   = dto.observaciones,
        fecha_ingreso   = dto.fecha_ingreso or date.today(),
        horario_trabajo = dto.horario_trabajo
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
