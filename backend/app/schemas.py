# app/schemas.py

from pydantic import BaseModel
from datetime import date
from typing import Optional, List, Dict


# ──────────────────────────────────────────────────────────
# DTOs de autenticación
# ──────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────
# admin_polo DTOs
# ──────────────────────────────────────────────────────────

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
    id_rol: int  # rol a asignar

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    password: Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# admin_polo: Empresas
# ──────────────────────────────────────────────────────────

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


class EmpresaAdminUpdate(BaseModel):
    """
    Solo admin_polo puede tocar nombre y rubro
    """
    nombre: Optional[str]
    rubro: Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# Sub-entidades: Vehículos, Contactos, Lotes, ServiciosPolo
# ──────────────────────────────────────────────────────────

## Vehículos
class VehiculoOut(BaseModel):
    id_vehiculo: int
    tipo: Optional[str]
    horarios: Optional[str]
    frecuencia: Optional[str]
    datos: Optional[dict]

    model_config = {"from_attributes": True}


class VehiculoCreate(BaseModel):
    tipo: Optional[str]
    horarios: Optional[str]
    frecuencia: Optional[str]
    datos: Optional[Dict]

    model_config = {"from_attributes": True}


class VehiculoUpdate(BaseModel):
    id_vehiculo: Optional[int]  # si viene, hago UPDATE
    tipo: Optional[str]
    horarios: Optional[str]
    frecuencia: Optional[str]
    datos: Optional[Dict]

    model_config = {"from_attributes": True}


## Contactos
class ContactoOut(BaseModel):
    id_contacto: int
    tipo: Optional[str]
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[dict]
    direccion: Optional[str]
    id_servicio_polo: Optional[int]

    model_config = {"from_attributes": True}


class ContactoCreate(BaseModel):
    tipo: Optional[str]
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[Dict]
    direccion: Optional[str]
    id_servicio_polo: int

    model_config = {"from_attributes": True}


class ContactoUpdate(BaseModel):
    id_contacto: Optional[int]
    tipo: Optional[str]
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[Dict]
    direccion: Optional[str]
    id_servicio_polo: Optional[int]

    model_config = {"from_attributes": True}


## Lotes (solo para ServicioPolo)
class LoteOut(BaseModel):
    id_lotes: int
    dueno: Optional[str]
    lote: Optional[int]
    manzana: Optional[int]

    model_config = {"from_attributes": True}


class LoteCreate(BaseModel):
    dueno: Optional[str]
    lote: Optional[int]
    manzana: Optional[int]

    model_config = {"from_attributes": True}


class LoteUpdate(BaseModel):
    id_lotes: Optional[int]
    dueno: Optional[str]
    lote: Optional[int]
    manzana: Optional[int]

    model_config = {"from_attributes": True}


## Servicios del Polo
class ServicioPoloOut(BaseModel):
    id_servicio_polo: int
    nombre: Optional[str]
    tipo: Optional[str]
    horario: Optional[str]
    datos: Optional[dict]
    lotes: List[LoteOut]

    model_config = {"from_attributes": True}


class ServicioPoloUpdate(BaseModel):
    id_servicio_polo: int
    nombre: Optional[str]
    tipo: Optional[str]
    horario: Optional[str]
    datos: Optional[dict]
    lotes: Optional[List[LoteUpdate]]

    model_config = {"from_attributes": True}

class ServicioOut(BaseModel):
    id_servicio: int
    nombre:      str
    tipo:        Optional[str]
    datos:       Optional[dict]

    model_config = {"from_attributes": True}


class ServiceCreate(BaseModel):
    nombre:      str
    descripcion: Optional[str]
    ubicacion:   Optional[str]
    disponibilidad: Optional[bool]
    horarios:    Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# Empresa detalle (para /me y full update)
# ──────────────────────────────────────────────────────────

class EmpresaDetailOut(BaseModel):
    cuil: int
    nombre: str
    rubro: str
    cant_empleados: int
    observaciones: Optional[str]
    fecha_ingreso: date
    horario_trabajo: str

    vehiculos: List[VehiculoOut]
    contactos: List[ContactoOut]
    servicios_polo: List[ServicioPoloOut]

    model_config = {"from_attributes": True}


# ─── Sólo campos que la empresa puede actualizar sobre sí misma ────────────────
class EmpresaSelfUpdate(BaseModel):
    cant_empleados:    Optional[int]
    observaciones:     Optional[str]
    horario_trabajo:   Optional[str]

    model_config = {"from_attributes": True}


# ─── Sólo campos que mostramos de vuelta después de la edición ────────────────
class EmpresaSelfOut(BaseModel):
    cant_empleados:    int
    observaciones:     Optional[str]
    horario_trabajo:   str

    model_config = {"from_attributes": True}



# ──────────────────────────────────────────────────────────
# Asignaciones (empresa → polo / empresa → propio)
# ──────────────────────────────────────────────────────────

class EmpresaServicioPoloAssign(BaseModel):
    id_servicio_polo: int

    model_config = {"from_attributes": True}


class EmpresaServicioAssign(BaseModel):
    id_servicio: int

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# Públicos (sin auth)
# ──────────────────────────────────────────────────────────

class ServicePublicOut(BaseModel):
    id_servicio: int
    nombre: str
    descripcion: Optional[str]
    ubicacion: Optional[str]
    disponibilidad: Optional[bool]
    horarios: Optional[str]

    model_config = {"from_attributes": True}


class CompanyFullOut(BaseModel):
    nombre: str
    rubro: str
    observaciones: Optional[str]
    horario_trabajo: str

    vehiculos: List[VehiculoOut]
    contactos: List[ContactoOut]
    servicios_polo: List[ServicioPoloOut]

    model_config = {"from_attributes": True}
