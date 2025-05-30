#schemas.py
from pydantic import BaseModel
from uuid import UUID  # Usamos UUID
from datetime import date
from typing import Optional, List, Dict


# ──────────────────────────────────────────────────────────
# DTOs de autenticación
# ──────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    nombre: str
    password: str
    cuil: int

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    nombre: str
    password: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
           from_attributes = True


# ──────────────────────────────────────────────────────────
# admin_polo DTOs
# ──────────────────────────────────────────────────────────

class RolOut(BaseModel):
    id_rol: int
    tipo_rol: str

    class Config:
           from_attributes = True


class UserOut(BaseModel):
    id_usuario: UUID  # Cambio a UUID
    nombre: str
    estado: bool  # Cambio a booleano
    cuil: int
    fecha_registro: date
    roles: List[RolOut]

    class Config:
           from_attributes = True


class UserCreate(BaseModel):
    nombre: str
    password: str
    cuil: int
    estado: Optional[bool] = True  # Asumimos estado por defecto a True
    id_rol: int  # Rol a asignar

    class Config:
           from_attributes = True


class UserUpdate(BaseModel):
    password: Optional[str]
    estado: Optional[bool]

    class Config:
           from_attributes = True
           
class UserUpdateCompany(BaseModel):
    password: Optional[str]

    class Config:
           from_attributes = True


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

    class Config:
           from_attributes = True


class EmpresaCreate(BaseModel):
    cuil: int
    nombre: str
    rubro: str
    cant_empleados: int
    observaciones: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    horario_trabajo: str

    class Config:
           from_attributes = True


class EmpresaAdminUpdate(BaseModel):
    """
    Solo admin_polo puede tocar nombre y rubro
    """
    nombre: Optional[str]
    rubro: Optional[str]

    class Config:
           from_attributes = True

# ──────────────────────────────────────────────────────────
# admin_polo: Servicios Polo
# ──────────────────────────────────────────────────────────

class ServicioPoloCreate(BaseModel):
    nombre: str
    horario: Optional[str]
    datos: Optional[dict]
    propietario: Optional[str]
    id_tipo_servicio_polo: Optional[int]
    cuil: int  # Este es el campo nuevo que relaciona con la empresa

    class Config:
        from_attributes = True


class ServicioPoloOut(BaseModel):
    id_servicio_polo: int
    nombre: str
    horario: Optional[str]
    datos: Optional[dict]
    propietario: Optional[str]
    id_tipo_servicio_polo: Optional[int]
    cuil: int  # Incluimos el cuil para la respuesta

    class Config:
        from_attributes = True


class LoteCreate(BaseModel):
    dueno: str
    lote: int
    manzana: int
    id_servicio_polo: int  # Esto debe ser el ID del servicio polo al cual se le asigna el lote

    class Config:
        from_attributes = True


class LoteOut(BaseModel):
    id_lotes: int
    dueno: str
    lote: int
    manzana: int
    id_servicio_polo: int

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────
# Sub-entidades: Vehículos, Contactos, Servicios para ADMINS EMPRESAS
# ──────────────────────────────────────────────────────────────────────────

## Vehículos
class VehiculoOut(BaseModel):
    id_vehiculo: int
    id_tipo_vehiculo: Optional[int]  # id del tipo de vehículo
    horarios: Optional[str]
    frecuencia: Optional[str]
    datos: Optional[dict]

    class Config:
        from_attributes = True


class VehiculoCreate(BaseModel):
    id_tipo_vehiculo: Optional[int]
    horarios: Optional[str]
    frecuencia: Optional[str]
    datos: Optional[Dict]

    class Config:
        from_attributes = True


class VehiculoUpdate(BaseModel):
    id_vehiculo: Optional[int]
    id_tipo_vehiculo: Optional[int]
    horarios: Optional[str]
    frecuencia: Optional[str]
    datos: Optional[Dict]

    class Config:
        from_attributes = True


## Servicios

class ServicioCreate(BaseModel):
    datos: Optional[dict] = None  # Datos adicionales
    id_tipo_servicio: int  # Referencia al tipo de servicio

    class Config:
        from_attributes = True


class ServicioUpdate(BaseModel):
    datos: Optional[dict]
    id_tipo_servicio: Optional[int]

    class Config:
        from_attributes = True


class ServicioOut(BaseModel):
    id_servicio: int
    datos: Optional[dict]
    id_tipo_servicio: int

    class Config:
        from_attributes = True



## Contactos

class ContactoOut(BaseModel):
    id_contacto: int
    id_tipo_contacto: Optional[int]
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[dict]
    direccion: Optional[str]
    id_servicio_polo: Optional[int]

    class Config:
        from_attributes = True


class ContactoCreate(BaseModel):
    id_tipo_contacto: Optional[int]
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[Dict]
    direccion: Optional[str]
    id_servicio_polo: int

    class Config:
        from_attributes = True


class ContactoUpdate(BaseModel):
    id_contacto: Optional[int]
    id_tipo_contacto: Optional[int]
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[Dict]
    direccion: Optional[str]
    id_servicio_polo: Optional[int]

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────
# Esquemas para la actualización de la empresa por el admin_empresa
# ──────────────────────────────────────────────────────────

class EmpresaSelfUpdate(BaseModel):
    cant_empleados: Optional[int]
    observaciones: Optional[str]
    horario_trabajo: Optional[str]

    class Config:
        from_attributes = True

class EmpresaSelfOut(BaseModel):
    cant_empleados: int
    observaciones: Optional[str]
    horario_trabajo: str

    class Config:
        from_attributes = True

# ──────────────────────────────────────────────────────────
# Esquema para los detalles completos de la empresa
# ──────────────────────────────────────────────────────────

class EmpresaDetailOut(BaseModel):
    cuil: int
    nombre: str
    rubro: str
    cant_empleados: int
    observaciones: Optional[str]
    fecha_ingreso: date
    horario_trabajo: str

    # Relaciones de la empresa
    vehiculos: List[VehiculoOut]
    contactos: List[ContactoOut]
    servicios_polo: List[ServicioPoloOut]
    servicios: List[ServicioOut]

    class Config:
        from_attributes = True

# ──────────────────────────────────────────────────────────
# Esquemas para la salida de detalles de la empresa para el público

class ContactoOutPublic(BaseModel):
    empresa_nombre: str # Nombre de la empresa asociada
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[Dict]
    direccion: Optional[str]
    tipo_contacto: Optional[str]  # Tipo de contacto
    class Config:
        from_attributes = True

class LoteOutPublic(BaseModel):
    empresa_nombre: str # Nombre de la empresa asociada
    lote: int
    manzana: int
    class Config:
        from_attributes = True

class ServicioPoloOutPublic(BaseModel):
    nombre: str
    horario: Optional[str]
    tipo_servicio_polo: Optional[str]  # Tipo de servicio del Polo
    lotes: List[LoteOut]  # Lotes asociados al servicio del polo

    class Config:
        from_attributes = True

class EmpresaDetailOutPublic(BaseModel):
    nombre: str
    rubro: str
    fecha_ingreso: date
    horario_trabajo: str
    contactos: List[ContactoOutPublic]  # Contactos de la empresa
    servicios_polo: List[ServicioPoloOutPublic]  # Servicios Polo asociados a la empresa

    class Config:
        from_attributes = True

    