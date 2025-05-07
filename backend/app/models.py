# app/models.py
from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.config import Base

class Empresa(Base):
    __tablename__ = "empresa"
    cuil            = Column(Integer,    primary_key=True, index=True)
    nombre          = Column(String,     nullable=False)
    rubro           = Column(String,     nullable=False)
    cant_empleados  = Column(Integer,    nullable=False)
    observaciones   = Column(Text)
    fecha_ingreso   = Column(Date,       nullable=False)
    horario_trabajo = Column(String,     nullable=False)
    usuarios        = relationship("Usuario", back_populates="empresa")

class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario     = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String,  unique=True, index=True)
    contrasena     = Column(String,  nullable=False)
    estado         = Column(String,  nullable=False)
    fecha_registro = Column(Date,    nullable=False)
    cuil           = Column(Integer, ForeignKey("empresa.cuil"))
    empresa        = relationship("Empresa", back_populates="usuarios")

class Rol(Base):
    __tablename__ = "rol"
    id_rol   = Column(Integer, primary_key=True, index=True)
    tipo_rol = Column(String,  nullable=False)
    usuarios = relationship(
        "Usuario",
        secondary="rol_usuario",
        back_populates="roles"
    )

class RolUsuario(Base):
    __tablename__ = "rol_usuario"
    id_rol     = Column(Integer, ForeignKey("rol.id_rol"),         primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), primary_key=True)

# Añadimos relación many-to-many en Usuario:
Usuario.roles = relationship(
    "Rol",
    secondary="rol_usuario",
    back_populates="usuarios"
)
