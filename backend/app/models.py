# app/models.py
import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    Text,
    ForeignKey,
    JSON,
    Time,
    BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config import Base
from datetime import date


# ─── Empresa y Usuario ────────────────────────────────────────────────────────

class Empresa(Base):
    __tablename__ = "empresa"
    cuil            = Column(Integer, primary_key=True, index=True)
    nombre          = Column(String,  nullable=False)
    rubro           = Column(String,  nullable=False)
    cant_empleados  = Column(Integer, nullable=False)
    observaciones   = Column(Text)
    fecha_ingreso   = Column(Date,    nullable=False)
    horario_trabajo = Column(String,  nullable=False)

    # relaciones con cascade delete-orphan
    usuarios        = relationship(
        "Usuario",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    vehiculos_emp   = relationship(
        "VehiculosEmpresa",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    contactos       = relationship(
        "Contacto",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    servicios_polo  = relationship(
        "ServicioPolo",  # Relación directa con ServicioPolo
        back_populates="empresa",  # Necesitas que esta relación también esté definida en ServicioPolo
        cascade="all, delete-orphan",  # Asegura que los registros se eliminen en cascada si se elimina la empresa
        passive_deletes=True,
    )
    servicios       = relationship(
        "EmpresaServicio",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    


class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario     = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    email          = Column(String,  unique=True, index=True, nullable=False)
    nombre         = Column(String,  unique=True, index=True)
    contrasena     = Column(String,  nullable=False)
    estado         = Column(Boolean,  nullable=False)
    fecha_registro = Column(Date,    nullable=False)
    cuil           = Column(
        Integer,
        ForeignKey("empresa.cuil", ondelete="CASCADE"),
        nullable=False,
    )

    empresa            = relationship(
        "Empresa",
        back_populates="usuarios",
        passive_deletes=True,
    )
    # Enlaces a roles: se borran antes de eliminar el Usuario
    rol_usuario_links  = relationship(
        "RolUsuario",
        back_populates="usuario",
        cascade="all, delete-orphan",
        # aquí no usamos passive_deletes para que SQLAlchemy genere DELETE en rol_usuario
    )
    # Many-to-many a Rol, a través de la tabla puente anterior
    roles              = relationship(
        "Rol",
        secondary="rol_usuario",
        back_populates="usuarios",
    )

    password_history = relationship(
        "PasswordHistory",
        back_populates="usuario",
        cascade="all, delete-orphan",
        order_by="PasswordHistory.created_at.desc()"
    )

class Rol(Base):
    __tablename__ = "rol"
    id_rol    = Column(Integer, primary_key=True, index=True)
    tipo_rol  = Column(String,  nullable=False)

    # Limpia primero los enlaces en rol_usuario
    rol_usuario_links = relationship(
        "RolUsuario",
        back_populates="rol",
        cascade="all, delete-orphan",
    )
    usuarios          = relationship(
        "Usuario",
        secondary="rol_usuario",
        back_populates="roles",
        overlaps="rol_usuario_links"  
    )


class RolUsuario(Base):
     __tablename__ = "rol_usuario"
     id_rol     = Column(
         Integer,
         ForeignKey("rol.id_rol", ondelete="CASCADE"),
         primary_key=True,
     )
    
     id_usuario = Column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        primary_key=True,
        default=uuid.uuid4
    )

     rol     = relationship("Rol",     back_populates="rol_usuario_links")
     usuario = relationship("Usuario", back_populates="rol_usuario_links")



# ─── Vehículos ───────────────────────────────────────────────────────────────

class TipoVehiculo(Base):
    __tablename__ = "tipo_vehiculo"  # singular, coincide con la tabla real
    id_tipo_vehiculo = Column(Integer, primary_key=True, index=True)
    tipo            = Column(String(100), nullable=False)

    vehiculos       = relationship("Vehiculo", back_populates="tipo_vehiculo")


class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id_vehiculo      = Column(Integer, primary_key=True, index=True)
    horarios         = Column(Text, nullable=False)  # en la tabla es text, no Time
    frecuencia       = Column(Text, nullable=False)
    datos            = Column(JSON, nullable=False)
    id_tipo_vehiculo = Column(
        Integer,
        ForeignKey("tipo_vehiculo.id_tipo_vehiculo", ondelete="CASCADE"),
        nullable=True,  # en tabla no tiene NOT NULL explícito
    )

    tipo_vehiculo   = relationship("TipoVehiculo", back_populates="vehiculos")
    empresas_emp    = relationship(
        "VehiculosEmpresa",
        back_populates="vehiculo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VehiculosEmpresa(Base):
    __tablename__ = "empresa_vehiculos"  # para que coincida con la tabla real
    id_vehiculo = Column(
        Integer,
        ForeignKey("vehiculos.id_vehiculo", ondelete="CASCADE"),
        primary_key=True,
    )
    cuil         = Column(
        BigInteger,  # para coincidir con bigint de la tabla
        ForeignKey("empresa.cuil", ondelete="CASCADE"),
        primary_key=True,
    )

    vehiculo     = relationship("Vehiculo", back_populates="empresas_emp")
    empresa      = relationship("Empresa", back_populates="vehiculos_emp")



# ─── Contactos ───────────────────────────────────────────────────────────────

class TipoContacto(Base):
    __tablename__ = "tipo_contacto"
    id_tipo_contacto = Column(Integer, primary_key=True, index=True)
    tipo             = Column(String,  nullable=False)

    contactos        = relationship("Contacto", back_populates="tipo_contacto")


class Contacto(Base):
    __tablename__ = "contacto"
    id_contacto      = Column(Integer, primary_key=True, index=True)
    nombre           = Column(String, nullable=False)
    telefono         = Column(String)
    datos            = Column(JSON)
    direccion        = Column(String)
    cuil_empresa     = Column(
        Integer,
        ForeignKey("empresa.cuil", ondelete="CASCADE"),
        nullable=False,
    )
    id_servicio_polo = Column(
        Integer,
        ForeignKey("servicio_polo.id_servicio_polo", ondelete="CASCADE"),
        nullable=False,
    )
    id_tipo_contacto = Column(
        Integer,
        ForeignKey("tipo_contacto.id_tipo_contacto", ondelete="CASCADE"),
        nullable=False,
    )

    empresa          = relationship("Empresa",       back_populates="contactos")
    servicio_polo    = relationship("ServicioPolo",  back_populates="contactos")
    tipo_contacto    = relationship("TipoContacto",  back_populates="contactos")


# ─── Servicios del Polo ───────────────────────────────────────────────────────

class TipoServicioPolo(Base):
    __tablename__ = "tipo_servicio_polo"
    id_tipo_servicio_polo = Column(Integer, primary_key=True, index=True)
    tipo                   = Column(String,  nullable=False)

    servicios              = relationship("ServicioPolo", back_populates="tipo_servicio")


class ServicioPolo(Base):
    __tablename__ = "servicio_polo"
    id_servicio_polo      = Column(Integer, primary_key=True, index=True)
    nombre                = Column(String, nullable=False)
    horario               = Column(String)
    datos                 = Column(JSON)
    propietario           = Column(Text)
    id_tipo_servicio_polo = Column(
        Integer,
        ForeignKey("tipo_servicio_polo.id_tipo_servicio_polo", ondelete="CASCADE"),
    )
    cuil                  = Column(Integer, ForeignKey("empresa.cuil", ondelete="CASCADE"), nullable=False)

    tipo_servicio         = relationship("TipoServicioPolo", back_populates="servicios")
    lotes = relationship(
    "Lote",
    back_populates="servicio_polo",
    cascade="all, delete-orphan",
    passive_deletes=True,
)
    contactos             = relationship("Contacto", back_populates="servicio_polo")
    empresa               = relationship("Empresa", back_populates="servicios_polo")  # Relación con Empresa

class Lote(Base):
    __tablename__ = "lotes"
    id_lotes          = Column(Integer, primary_key=True, index=True)
    id_servicio_polo  = Column(
        Integer,
        ForeignKey("servicio_polo.id_servicio_polo", ondelete="CASCADE"),
        nullable=False,
    )
    dueno             = Column(String,  nullable=False)
    lote              = Column(Integer, nullable=False)
    manzana           = Column(Integer, nullable=False)

    servicio_polo     = relationship("ServicioPolo", back_populates="lotes")



# ─── Servicios Propios ────────────────────────────────────────────────────────

class TipoServicio(Base):
    __tablename__ = "tipo_servicio"
    id_tipo_servicio = Column(Integer, primary_key=True, index=True)
    tipo             = Column(String,  nullable=False)

    servicios        = relationship("Servicio", back_populates="tipo_servicio")


class Servicio(Base):
    __tablename__ = "servicio"
    id_servicio      = Column(Integer, primary_key=True, index=True)
    datos            = Column(JSON)
    id_tipo_servicio = Column(
        Integer,
        ForeignKey("tipo_servicio.id_tipo_servicio", ondelete="CASCADE"),
    )

    tipo_servicio    = relationship("TipoServicio", back_populates="servicios")
    empresas_servicio = relationship(
        "EmpresaServicio",
        back_populates="servicio",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EmpresaServicio(Base):
    __tablename__ = "empresa_servicio"
    
    cuil = Column(
        Integer,
        ForeignKey("empresa.cuil", ondelete="CASCADE"),
        primary_key=True,
    )
    id_servicio = Column(
        Integer,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
        primary_key=True,
    )

    empresa = relationship("Empresa", back_populates="servicios")
    servicio = relationship("Servicio", back_populates="empresas_servicio")

class PasswordHistory(Base):
    __tablename__ = "password_history"
    
    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False
    )
    password_hash = Column(String, nullable=False)
    created_at = Column(Date, nullable=False, default=date.today)
   
    usuario = relationship("Usuario", back_populates="password_history")