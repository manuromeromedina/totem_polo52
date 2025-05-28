# app/services.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM

# Contexto para bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tiempo de expiración por defecto (minutos)
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    """
    Hashea la contraseña en claro usando bcrypt.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que la contraseña en claro coincida con el hash almacenado.
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Genera un JWT incluyendo los campos de `data` y un 'exp' que vence tras
    ACCESS_TOKEN_EXPIRE_MINUTES (o el expires_delta pasado).
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token
