from pydantic import BaseModel
from datetime import date
from typing import Optional, List, Dict

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
    id_rol: int  # rol a asignar al crearlo

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    password: Optional[str]

    model_config = {"from_attributes": True}


# ─── DTOs para Empresas (admin_polo) ──────────────────────────────────────────

class EmpresaOut(BaseModel):
    cuil: int
    nombre: str
    rubro: str
    cant_empleados: int
    observaciones: Optional[str]
    fecha_ingreso: date
    horario_trabajo: str

    model_config = {"from_attributes": True}


class EmpresaCreate(BaseModel):
    cuil: int
    nombre: str
    rubro: str
    cant_empleados: int
    observaciones: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    horario_trabajo: str

    model_config = {"from_attributes": True}


class EmpresaUpdate(BaseModel):
    nombre: Optional[str]
    rubro: Optional[str]
    cant_empleados: Optional[int]
    observaciones: Optional[str]
    fecha_ingreso: Optional[date]
    horario_trabajo: Optional[str]

    model_config = {"from_attributes": True}


# ─── Esquemas para Usuario de Empresa ─────────────────────────────────────────

class MeOut(BaseModel):
    user: UserOut
    empresa: EmpresaOut

    model_config = {"from_attributes": True}


class UserPasswordUpdate(BaseModel):
    password: str

    model_config = {"from_attributes": True}


class EmpresaSelfUpdate(BaseModel):
    cant_empleados: Optional[int]
    observaciones: Optional[str]
    horario_trabajo: Optional[str]

    model_config = {"from_attributes": True}


class InternalOut(BaseModel):
    dotacion: int                # reutilizamos cant_empleados
    energia: Optional[float]     # si lo tuvieras en otra tabla
    residuos: Optional[float]    # idem

    model_config = {"from_attributes": True}


# ─── Public DTOs (sin auth) ──────────────────────────────────────────────────

class EmpresaPublicOut(BaseModel):
    cuil: int
    nombre: str
    rubro: str
    fecha_ingreso: date

    model_config = {"from_attributes": True}


class ServicePublicOut(BaseModel):
    id_servicio: int
    nombre: str
    descripcion: Optional[str]
    ubicacion: Optional[str]
    disponibilidad: Optional[bool]
    horarios: Optional[str]

    model_config = {"from_attributes": True}


# ─── DTOs de salida para entidades relacionadas ────────────────────────────────

# ─── Vehículos ───────────────────────────────────────────────────────────────

class VehiculoOut(BaseModel):
    id_vehiculo: int
    tipo:        Optional[str]
    horarios:    Optional[str]
    frecuencia:  Optional[str]
    datos:       Optional[dict]

    model_config = {"from_attributes": True}

class VehiculoUpdate(BaseModel):
    id_vehiculo: Optional[int]  # si viene, es un UPDATE; si no, es un CREATE
    tipo:        Optional[str]
    horarios:    Optional[str]
    frecuencia:  Optional[str]
    datos:       Optional[dict]

    model_config = {"from_attributes": True}


# ─── Contactos ───────────────────────────────────────────────────────────────

class ContactoOut(BaseModel):
    id_contacto:      int
    tipo:             Optional[str]
    nombre:           Optional[str]
    telefono:         Optional[str]
    datos:            Optional[dict]
    direccion:        Optional[str]
    id_servicio_polo: Optional[int]

    model_config = {"from_attributes": True}

class ContactoUpdate(BaseModel):
    id_contacto:      Optional[int]
    tipo:             Optional[str]
    nombre:           Optional[str]
    telefono:         Optional[str]
    datos:            Optional[dict]
    direccion:        Optional[str]
    id_servicio_polo: Optional[int]

    model_config = {"from_attributes": True}


# ─── Lotes ───────────────────────────────────────────────────────────────────

class LoteOut(BaseModel):
    id_lote:          int
    dueno:            Optional[str]
    lote:             Optional[int]
    manzana:          Optional[int]

    model_config = {"from_attributes": True}

class LoteUpdate(BaseModel):
    id_lote: Optional[int]
    dueno:   Optional[str]
    lote:    Optional[int]
    manzana: Optional[int]

    model_config = {"from_attributes": True}


# ─── Servicios del Polo ─────────────────────────────────────────────────────

class ServicioPoloOut(BaseModel):
    id_servicio_polo: int
    nombre:            Optional[str]
    tipo:              Optional[str]
    horario:           Optional[str]
    datos:             Optional[dict]
    lotes:             List[LoteOut]  # todos los lotes de este servicio

    model_config = {"from_attributes": True}

class ServicioPoloUpdate(BaseModel):
    id_servicio_polo: int                # obligatorio para referenciar
    nombre:            Optional[str]
    tipo:              Optional[str]
    horario:           Optional[str]
    datos:             Optional[dict]
    lotes:             Optional[List[LoteUpdate]]  # si viene, actualiza/upserta lotes

    model_config = {"from_attributes": True}


# ─── Empresa detalle completo ────────────────────────────────────────────────

class EmpresaDetailOut(BaseModel):
    cuil:            int
    nombre:          str
    rubro:           str
    cant_empleados:  int
    observaciones:   Optional[str]
    fecha_ingreso:   date
    horario_trabajo: str

    vehiculos:       List[VehiculoOut]
    contactos:       List[ContactoOut]
    servicios_polo:  List[ServicioPoloOut]

    model_config = {"from_attributes": True}


class EmpresaDetailUpdate(BaseModel):
    # campos directos de empresa (no cuil ni fecha_ingreso)
    nombre:          Optional[str]
    rubro:           Optional[str]
    cant_empleados:  Optional[int]
    observaciones:   Optional[str]
    horario_trabajo: Optional[str]

    # colecciones anidadas
    vehiculos:       Optional[List[VehiculoUpdate]]
    contactos:       Optional[List[ContactoUpdate]]
    servicios_polo:  Optional[List[ServicioPoloUpdate]]

    model_config = {"from_attributes": True}
