from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt

from app import models, schemas, services
from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app.services import hash_password, verify_password, create_access_token

# Definición de la aplicación FastAPI
app = FastAPI()

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Función para obtener el usuario actual desde el token JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_email  # Aquí debes buscar el usuario en la base de datos usando el correo
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Middleware para verificar que el usuario sea un admin
def require_admin_role(current_user: str = Depends(get_current_user)):
    db = SessionLocal()
    db_user = db.query(models.User).filter(models.User.email == current_user).first()
    if db_user is None or db_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return db_user

# Ruta para registrar un nuevo usuario (solo accesible para admins)
@app.post("/register")
def register(user: schemas.UserRegister, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin_role)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = services.hash_password(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}


# Ruta para login (iniciar sesión)
@app.post("/login")
async def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    # Verificar que el usuario exista y la contraseña sea válida
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user is None or not services.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Crear y devolver el token JWT
    access_token = services.create_access_token(data={"sub": db_user.email, "role": db_user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# Ruta para obtener información de la empresa (solo para admins o usuarios de la empresa)
@app.get("/company-info")
async def get_company_info(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == current_user).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.role == "admin":
        # Si es admin, devolver toda la información de la empresa
        company_data = db.query(models.Company).all()
        return company_data
    elif db_user.role == "empresa":
        # Si es una empresa, devolver solo la información de la empresa del usuario
        company_data = db.query(models.Company).filter(models.Company.id == db_user.company_id).first()
        return company_data
    else:
        raise HTTPException(status_code=403, detail="Access denied for your role")

# Middleware para requerir rol de admin para acceder a rutas específicas
def require_admin_role(current_user: models.User = Depends(get_current_user)):
    db = SessionLocal()
    db_user = db.query(models.User).filter(models.User.email == current_user).first()
    if db_user is None or db_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return db_user
