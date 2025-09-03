#app/schemas.py
from pydantic import BaseModel, Field, EmailStr, field_validator
from uuid import UUID
from datetime import date
from typing import Optional, List, Dict
import re

PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$'

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════════════

class UserLogin(BaseModel):
    identifier: str = Field(
        ..., min_length=3, max_length=255,
        description="Nombre de usuario o email"
    )
    password: str = Field(
        ..., min_length=8, max_length=128,
        description="Password registrada"
    )

    class Config:
        from_attributes = True

class UserRegister(BaseModel):
    nombre: str = Field(
        ..., min_length=3, max_length=50,
        description="Entre 3 y 50 caracteres"
    )
    email: EmailStr = Field(
        ..., max_length=255,
        description="Email válido"
    )
    password: str = Field(
        ..., min_length=8, max_length=128,
        description=(
            "8–128 caracteres, al menos una mayúscula, "
            "una minúscula y un dígito"
        ),
    )
    cuil: int = Field(
        ..., gt=0,
        description="CUIL numérico positivo"
    )

    @field_validator('password')
    def password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un dígito')
        return v

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    tipo_rol: str 
    remember_me: Optional[bool] = False  # NUEVO: Campo para recordarme

    class Config:
           from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE RECUPERACIÓN DE CONTRASEÑA
# ═══════════════════════════════════════════════════════════════════

class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(
        ..., max_length=255,
        description="Email registrado"
    )
    
    class Config:
        from_attributes = True

class PasswordResetConfirm(BaseModel):
    token: str = Field(
        ..., description="Token de recuperación válido"
    )
    new_password: str = Field(
        ..., min_length=8, max_length=128,
        description=(
            "8–128 caracteres, al menos una mayúscula, una minúscula "
            "y un dígito"
        ),
    )

    @field_validator('new_password')
    def password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un dígito')
        return v

    class Config:
        from_attributes = True

class PasswordResetConfirmSecure(BaseModel):
    """Schema para confirmación segura de reset (requiere contraseña actual y confirmación) - SOLO PARA USUARIOS LOGUEADOS"""
    token: str = Field(..., description="Token de recuperación válido")
    current_password: str = Field(..., min_length=1, description="Contraseña actual del usuario")
    new_password: str = Field(
        ..., min_length=8, max_length=128,
        description="Nueva contraseña (8-128 caracteres, mayúscula, minúscula, dígito)"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=128,
        description="Confirmar nueva contraseña (debe coincidir con new_password)"
    )

    @field_validator('new_password')
    def password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un dígito')
        return v

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        """Validar que las contraseñas coincidan"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

    class Config:
        from_attributes = True

class ForgotPasswordReset(BaseModel):
    """Schema para reset de contraseña olvidada (solo token + nueva contraseña x2)"""
    token: str = Field(..., description="Token de recuperación válido del email")
    new_password: str = Field(
        ..., min_length=8, max_length=128,
        description="Nueva contraseña (8-128 caracteres, mayúscula, minúscula, dígito)"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=128,
        description="Confirmar nueva contraseña (debe coincidir con new_password)"
    )

    @field_validator('new_password')
    def password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un dígito')
        return v

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        """Validar que las contraseñas coincidan"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

    class Config:
        from_attributes = True

class ChangePasswordDirect(BaseModel):
    """Schema para cambio directo de contraseña (sin email, usuario logueado)"""
    current_password: str = Field(..., min_length=1, description="Contraseña actual del usuario")
    new_password: str = Field(
        ..., min_length=8, max_length=128,
        description="Nueva contraseña (8-128 caracteres, mayúscula, minúscula, dígito)"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=128,
        description="Confirmar nueva contraseña (debe coincidir con new_password)"
    )

    @field_validator('new_password')
    def password_complexity(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un dígito')
        return v

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        """Validar que las contraseñas coincidan"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

    class Config:
        from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS PARA FUNCIONALIDAD "RECORDARME"
# ═══════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    """Schema para login con opción de recordarme"""
    username: str = Field(..., min_length=1, description="Nombre de usuario o email")
    password: str = Field(..., min_length=1, description="Contraseña")
    remember_me: Optional[bool] = Field(False, description="Recordar sesión por 30 días")
    
    class Config:
        from_attributes = True

class RememberSessionResponse(BaseModel):
    """Response para verificación de sesión recordada"""
    logged_in: bool
    user: Optional[Dict] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserSessionInfo(BaseModel):
    """Información del usuario para sesión recordada"""
    nombre: str
    email: str
    tipo_rol: str
    
    class Config:
        from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE TIPOS/CATÁLOGOS
# ═══════════════════════════════════════════════════════════════════

class TipoVehiculoOut(BaseModel):
    id_tipo_vehiculo: int
    tipo: str

    class Config:
        from_attributes = True

class TipoServicioOut(BaseModel):
    id_tipo_servicio: int
    tipo: str

    class Config:
        from_attributes = True

class TipoContactoOut(BaseModel):
    id_tipo_contacto: int
    tipo: str

    class Config:
        from_attributes = True

class TipoServicioPoloOut(BaseModel):
    id_tipo_servicio_polo: int
    tipo: str

    class Config:
        from_attributes = True

class RolOut(BaseModel):
    id_rol: int
    tipo_rol: str

    class Config:
           from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE USUARIOS
# ═══════════════════════════════════════════════════════════════════

class UserOut(BaseModel):
    id_usuario: UUID
    email: EmailStr
    nombre: str
    estado: bool
    cuil: int
    fecha_registro: date
    roles: List[RolOut]

    class Config:
           from_attributes = True

class UserCreate(BaseModel):
    nombre: str = Field(
        ..., min_length=3, max_length=50,
        description="Entre 3 y 50 caracteres"
    )
    email: EmailStr = Field(
        ..., max_length=255,
        description="Email válido"
    )
    cuil: int = Field(
        ..., gt=0,
        description="CUIL numérico positivo"
    )
    estado: Optional[bool] = Field(
        True,
        description="True = activo, False = inactivo"
    )
    id_rol: int = Field(
        ..., gt=0,
        description="ID del rol a asignar (>0)"
    )
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    password: Optional[str] = Field(
        None, min_length=8, max_length=128,
        description="Si se envía, aplica mismas reglas de complejidad"
    )
    estado: Optional[bool] = Field(
        None,
        description="True = activo, False = inactivo"
    )

    @field_validator('password')
    def password_complexity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un dígito')
        return v

    class Config:
        from_attributes = True

class UserUpdateCompany(BaseModel):
    password: Optional[str] = Field(
        None, min_length=8, max_length=128,
        description="Si se envía, aplica mismas reglas de complejidad"
    )

    @field_validator('password')
    def password_complexity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un dígito')
        return v

    class Config:
        from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE EMPRESAS
# ═══════════════════════════════════════════════════════════════════

class EmpresaOut(BaseModel):
    cuil: int
    nombre: str
    rubro: str
    cant_empleados: int
    observaciones: Optional[str] = None
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
    """Solo admin_polo puede tocar nombre y rubro"""
    nombre: Optional[str]
    rubro: Optional[str]

    class Config:
           from_attributes = True

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

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE SERVICIOS DEL POLO
# ═══════════════════════════════════════════════════════════════════

class ServicioPoloCreate(BaseModel):
    nombre: str
    horario: Optional[str]
    datos: Optional[dict]
    propietario: Optional[str]
    id_tipo_servicio_polo: Optional[int]
    cuil: int

    class Config:
        from_attributes = True

class ServicioPoloOut(BaseModel):
    id_servicio_polo: int
    nombre: str
    horario: Optional[str] = None
    datos: Optional[dict] = None
    propietario: Optional[str] = None
    id_tipo_servicio_polo: int
    cuil: int
    tipo_servicio_polo: Optional[str] = None

    class Config:
        from_attributes = True

class ServicioPoloOutPublic(BaseModel):
    nombre: str
    horario: Optional[str]
    tipo_servicio_polo: Optional[str]
    lotes: List["LoteOut"]

    class Config:
        from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE LOTES
# ═══════════════════════════════════════════════════════════════════

class LoteCreate(BaseModel):
    dueno: str
    lote: int
    manzana: int
    id_servicio_polo: Optional[int] = None

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

class LoteOutPublic(BaseModel):
    empresa_nombre: str
    lote: int
    manzana: int
    
    class Config:
        from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE VEHÍCULOS
# ═══════════════════════════════════════════════════════════════════

class VehiculoOut(BaseModel):
    id_vehiculo: int
    id_tipo_vehiculo: int
    horarios: str
    frecuencia: str
    datos: dict
    tipo_vehiculo: Optional[TipoVehiculoOut] = None

    class Config:
        from_attributes = True

class VehiculoCreate(BaseModel):
    id_tipo_vehiculo: int
    horarios: str
    frecuencia: str
    datos: dict = {}

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

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE SERVICIOS (EMPRESARIALES)
# ═══════════════════════════════════════════════════════════════════

class ServicioCreate(BaseModel):
    datos: Optional[dict] = None
    id_tipo_servicio: int

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

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DE CONTACTOS
# ═══════════════════════════════════════════════════════════════════

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

class ContactoOutPublic(BaseModel):
    empresa_nombre: str
    nombre: Optional[str]
    telefono: Optional[str]
    datos: Optional[Dict]
    direccion: Optional[str]
    tipo_contacto: Optional[str]
    
    class Config:
        from_attributes = True

# ═══════════════════════════════════════════════════════════════════
# SCHEMAS DETALLADOS Y COMPLEJOS
# ═══════════════════════════════════════════════════════════════════

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
    servicios: List[ServicioOut]

    class Config:
        from_attributes = True

class EmpresaDetailOutPublic(BaseModel):
    nombre: str
    rubro: str
    fecha_ingreso: date
    horario_trabajo: str
    contactos: List[ContactoOutPublic]
    servicios_polo: List[ServicioPoloOutPublic]

    class Config:
        from_attributes = True

class PoloSelfUpdate(BaseModel):
    """Schema para actualizar datos del polo por sí mismo"""
    cant_empleados: int
    horario_trabajo: str
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True

class PoloDetailOut(BaseModel):
    """Schema para devolver información completa del polo"""
    # Datos del polo (empresa específica)
    cuil: int
    nombre: str
    rubro: str
    cant_empleados: int
    fecha_ingreso: date
    horario_trabajo: str
    observaciones: Optional[str] = None
    
    # Listas de entidades que gestiona el polo
    empresas: List[EmpresaOut]
    servicios_polo: List[ServicioPoloOut]
    usuarios: List[UserOut]
    lotes: List[LoteOut]
    
    class Config:
        from_attributes = True


#-------------#
class UserLimitIncreaseRequest(BaseModel):
    cuil_empresa: int = Field(..., gt=0, description="CUIL de la empresa que solicita")
    justificacion: str = Field(..., min_length=20, max_length=500, description="Justificación de la solicitud")
    usuarios_adicionales_solicitados: int = Field(..., gt=0, le=10, description="Cantidad de usuarios adicionales solicitados")
    
    class Config:
        from_attributes = True