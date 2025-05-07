from fastapi import APIRouter, HTTPException, Depends
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

@router.get("/", response_model=list[schemas.UserOut], summary="Listar usuarios")
def list_users(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()

@router.get("/{user_id}", response_model=schemas.UserOut, summary="Ver usuario")
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(404, "Usuario no existe")
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
    # 1) valida unicidad
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(400, "Ya existe un usuario con ese nombre")

    # 2) crea el Usuario
    new_user = models.Usuario(
        nombre=dto.nombre,
        contrasena=services.hash_password(dto.password),
        estado=dto.estado,
        fecha_registro=date.today(),
        cuil=dto.cuil,
    )
    db.add(new_user)
    db.flush()  # fuerza INSERT para obtener new_user.id_usuario

    # 3) busca el rol
    rol = db.query(models.Rol).filter(models.Rol.id_rol == dto.id_rol).first()
    if not rol:
        raise HTTPException(400, "Rol inválido")

    # 4) crea el enlace en la tabla pasarela
    enlace = models.RolUsuario(
        id_usuario=new_user.id_usuario,
        id_rol=rol.id_rol
    )
    db.add(enlace)

    # 5) confirma todo
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/{user_id}", response_model=schemas.UserOut, summary="Actualizar usuario")
def update_user(user_id: int, dto: schemas.UserUpdate, db: Session = Depends(get_db)):
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(404, "Usuario no existe")
    if dto.password:
        u.contrasena = services.hash_password(dto.password)
    if dto.estado:
        u.estado = dto.estado
    db.commit()
    db.refresh(u)
    return u

@router.delete("/{user_id}", status_code=204, summary="Eliminar usuario")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(models.Usuario).get(user_id)
    if not u:
        raise HTTPException(404, "Usuario no existe")
    db.delete(u)
    db.commit()
