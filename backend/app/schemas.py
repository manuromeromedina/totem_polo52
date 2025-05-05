# app/schemas.py

from pydantic import BaseModel

class UserRegister(BaseModel):
    nombre: str
    password: str
    cuil: int         # lo necesitas para la FK

    class Config:
        from_attributes = True  # pydantic v2

class UserLogin(BaseModel):
    nombre: str
    password: str
