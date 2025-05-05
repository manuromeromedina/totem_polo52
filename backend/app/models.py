# app/models.py

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.config import Base

class Empresa(Base):
    __tablename__ = "empresa"

    cuil            = Column(Integer, primary_key=True, index=True)
    nombre          = Column(String, nullable=False)
    rubro           = Column(String, nullable=False)
    cant_empleados  = Column(Integer, nullable=False)
    observaciones   = Column(Text)            # TEXT en tu BD
    fecha_ingreso   = Column(Date, nullable=False)
    horario_trabajo = Column(String, nullable=False)

    usuarios = relationship("Usuario", back_populates="empresa")


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario     = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String, unique=True, index=True)
    contrasena     = Column(String, nullable=False)          # corresponde al campo 'contrasena'
    estado         = Column(String, nullable=False)
    fecha_registro = Column(Date, nullable=False)
    cuil           = Column(Integer, ForeignKey("empresa.cuil"))  # FK a empresa

    empresa = relationship("Empresa", back_populates="usuarios")
