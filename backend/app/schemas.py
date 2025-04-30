from pydantic import BaseModel

# Esquema para el registro de un nuevo usuario
class UserRegister(BaseModel):
    nombre: str  # Cambié 'email' por 'nombre'
    password: str
    role: str  # 'admin', 'admin_empresa', 'usuario'

    class Config:
        orm_mode = True

# Esquema para el login
class UserLogin(BaseModel):
    nombre: str  # Cambié 'email' por 'nombre'
    password: str
