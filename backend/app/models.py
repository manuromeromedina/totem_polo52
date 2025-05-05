# app/models.py
from sqlalchemy import Column, Integer, String, Date, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.config import Base

class User(Base):
    __tablename__ = "usuario"      # coincide con tu tabla real
    __table_args__ = {"schema": "public"}  # opcional si tenés otro schema

    id_usuario    = Column(Integer,    primary_key=True, index=True)
    nombre        = Column(String,     unique=True,      index=True)
    contrasena    = Column(String)     # aquí está tu hash
    estado        = Column(String)
    fecha_registro= Column(Date)
    cuil          = Column(BigInteger)
    # si en tu BD tenés FK a empresa:
    empresa_id    = Column(Integer, ForeignKey("empresa.id_empresa"))
    empresa       = relationship("Company", back_populates="users")

class Company(Base):
    __tablename__ = "empresa"       # tu tabla real de empresas
    __table_args__ = {"schema": "public"}

    id_empresa    = Column(Integer, primary_key=True, index=True)
    nombre        = Column(String)
    users         = relationship("User", back_populates="empresa")
