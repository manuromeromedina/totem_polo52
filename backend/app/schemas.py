# app/schemas.py

from pydantic import BaseModel
from datetime import date
from typing import Optional, List

# ─── Auth DTOs ────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    nombre: str
    password: str
    cuil: int

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    nombre: str
    password: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str

    model_config = {"from_attributes": True}


# ─── admin_polo DTOs ──────────────────────────────────────────────────────────

class RolOut(BaseModel):
    id_rol: int
    tipo_rol: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id_usuario: int
    nombre: str
    estado: str
    cuil: int
    fecha_registro: date
    roles: List[RolOut]

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    nombre: str
    password: str
    cuil: int
    estado: Optional[str] = "activo"
    tipo_rol: str   # aquí indicamos qué rol asignar al crearlo
    id_rol:   int 
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    password: Optional[str]

    model_config = {"from_attributes": True}

# ---------------------------------------------------
# DTOs para Empresas
# ---------------------------------------------------

class EmpresaOut(BaseModel):
    cuil:            int
    nombre:          str
    rubro:           str
    cant_empleados:  int
    observaciones:   Optional[str]
    fecha_ingreso:   date
    horario_trabajo: str

    model_config = {"from_attributes": True}


class EmpresaCreate(BaseModel):
    cuil:            int
    nombre:          str
    rubro:           str
    cant_empleados:  int
    observaciones:   Optional[str] = None
    fecha_ingreso:   Optional[date] = None
    horario_trabajo: str

    model_config = {"from_attributes": True}


class EmpresaUpdate(BaseModel):
    nombre:          Optional[str]
    rubro:           Optional[str]
    cant_empleados:  Optional[int]
    observaciones:   Optional[str]
    fecha_ingreso:   Optional[date]
    horario_trabajo: Optional[str]

    model_config = {"from_attributes": True}


# -----------------------------------------------------------------------------
# Esquemas específicos para "Usuario de Empresa"
# -----------------------------------------------------------------------------

class MeOut(BaseModel):
    user: UserOut
    empresa: EmpresaOut

    model_config = {"from_attributes": True}


class EmpresaSelfUpdate(BaseModel):
    cant_empleados: Optional[int]
    observaciones: Optional[str]
    horario_trabajo: Optional[str]

    model_config = {"from_attributes": True}


class InternalOut(BaseModel):
    dotacion: int                 # reutilizamos cant_empleados
    energia: Optional[float]      # si lo tuvieras en otra tabla
    residuos: Optional[float]     # idem

    model_config = {"from_attributes": True}

class UserPasswordUpdate(BaseModel):
    password: str

    model_config = {"from_attributes": True}
