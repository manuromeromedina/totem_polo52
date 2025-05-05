# app/main.py

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from jose import JWTError, jwt

from app import models, schemas, services
from app.config import SessionLocal, SECRET_KEY, ALGORITHM

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ... (funciones de JWT idénticas) ...

@app.post("/register")
def register(dto: schemas.UserRegister, db: Session = Depends(get_db)):
    # Validar nombre único
    if db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first():
        raise HTTPException(400, "Ya existe ese nombre")

    # Crear usuario
    new = models.Usuario(
        nombre=dto.nombre,
        contrasena=services.hash_password(dto.password),
        estado="activo",
        fecha_registro=date.today(),
        cuil=dto.cuil,             # ahora debes enviar el CUIL en tu DTO
    )
    db.add(new)
    db.commit()
    return {"message": "Usuario creado"}

@app.post("/login")
def login(dto: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.nombre == dto.nombre).first()
    if not user or not services.verify_password(dto.password, user.contrasena):
        raise HTTPException(401, "Credenciales inválidas")

    token = services.create_access_token({"sub": user.nombre})
    return {"access_token": token, "token_type": "bearer"}
