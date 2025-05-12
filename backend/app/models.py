# app/models.py

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.config import Base

class Empresa(Base):
    __tablename__ = "empresa"
    cuil            = Column(Integer, primary_key=True, index=True)
    nombre          = Column(String,  nullable=False)
    rubro           = Column(String,  nullable=False)
    cant_empleados  = Column(Integer, nullable=False)
    observaciones   = Column(Text)
    fecha_ingreso   = Column(Date,    nullable=False)
    horario_trabajo = Column(String,  nullable=False)

    # Cuando se borra una Empresa, se borran en cascada todos estos hijos:
    usuarios        = relationship(
        "Usuario",
        back_populates="empresa",
        cascade="all, delete-orphan",
        #passive_deletes=True,
    )
    vehiculos       = relationship(
        "Vehiculo",
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
        "EmpresaServicioPolo",
        back_populates="empresa",
        cascade="all, delete-orphan",
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
    id_usuario     = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String,  unique=True, index=True)
    contrasena     = Column(String,  nullable=False)
    estado         = Column(String,  nullable=False)
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
    )


class RolUsuario(Base):
     __tablename__ = "rol_usuario"
     id_rol     = Column(
         Integer,
         ForeignKey("rol.id_rol", ondelete="CASCADE"),
         primary_key=True,
     )
     id_usuario = Column(
         Integer,
         ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
         primary_key=True,
     )

     rol     = relationship("Rol",     back_populates="rol_usuario_links")
     usuario = relationship("Usuario", back_populates="rol_usuario_links")



class ServicioPolo(Base):
    __tablename__ = "servicio_polo"
    id_servicio_polo = Column(Integer, primary_key=True, index=True)
    nombre            = Column(String,  nullable=False)
    tipo              = Column(String,  nullable=False)
    horario           = Column(String)
    datos             = Column(JSON)

    lotes         = relationship(
        "Lote",
        back_populates="servicio_polo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    contactos     = relationship(
        "Contacto",
        back_populates="servicio_polo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    empresas      = relationship(
        "EmpresaServicioPolo",
        back_populates="servicio_polo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Lote(Base):
    __tablename__ = "lotes"
    id_lote            = Column(Integer, primary_key=True, index=True)
    id_servicio_polo   = Column(
        Integer,
        ForeignKey("servicio_polo.id_servicio_polo", ondelete="CASCADE"),
        nullable=False,
    )
    dueno              = Column(String)
    lote               = Column(Integer)
    manzana            = Column(Integer)

    servicio_polo      = relationship("ServicioPolo", back_populates="lotes")


class EmpresaServicioPolo(Base):
    __tablename__ = "empresa_servicio_polo"
    cuil             = Column(
        Integer,
        ForeignKey("empresa.cuil", ondelete="CASCADE"),
        primary_key=True,
    )
    id_servicio_polo = Column(
        Integer,
        ForeignKey("servicio_polo.id_servicio_polo", ondelete="CASCADE"),
        primary_key=True,
    )

    empresa          = relationship("Empresa",      back_populates="servicios_polo")
    servicio_polo    = relationship("ServicioPolo", back_populates="empresas")


class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id_vehiculo = Column(Integer, primary_key=True, index=True)
    cuil         = Column(
        Integer,
        ForeignKey("empresa.cuil", ondelete="CASCADE"),
        nullable=False,
    )
    tipo         = Column(String)
    horarios     = Column(String)
    frecuencia   = Column(String)
    datos        = Column(JSON)

    empresa      = relationship("Empresa", back_populates="vehiculos")


class Contacto(Base):
    __tablename__ = "contacto"
    id_contacto      = Column(Integer, primary_key=True, index=True)
    tipo             = Column(String)
    nombre           = Column(String)
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

    empresa          = relationship("Empresa",      back_populates="contactos")
    servicio_polo    = relationship("ServicioPolo", back_populates="contactos")


class EmpresaServicio(Base):
    __tablename__ = "empresa_servicio"
    cuil            = Column(
        Integer,
        ForeignKey("empresa.cuil", ondelete="CASCADE"),
        primary_key=True,
    )
    id_servicio     = Column(
        Integer,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
        primary_key=True,
    )

    empresa         = relationship("Empresa",          back_populates="servicios")
    servicio        = relationship("Servicio",         back_populates="empresas")


class Servicio(Base):
    __tablename__ = "servicio"
    id_servicio    = Column(Integer, primary_key=True)
    nombre         = Column(String, nullable=False)

    empresas       = relationship(
        "EmpresaServicio",
        back_populates="servicio",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
