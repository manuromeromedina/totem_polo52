from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt

from app import models, schemas, services
from app.config import SessionLocal, SECRET_KEY, ALGORITHM
from app.services import hash_password, verify_password, create_access_token

# Configuración de OAuth2 para manejar el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Función para obtener el usuario actual desde el token JWT
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_name: str = payload.get("sub")
        if user_name is None:
            raise credentials_exception
        user = db.query(models.User).filter(models.User.nombre == user_name).first()  # Aquí usamos 'nombre'
        if user is None:
            raise credentials_exception
        return user  # Retorna el usuario obtenido de la base de datos
    except JWTError:
        raise credentials_exception

# Middleware para verificar si el usuario tiene el rol de admin
def require_admin_role(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can register users.")
    return current_user

# Crear instancia de FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the API! Use /docs for the Swagger documentation."}

# Ruta para registrar un nuevo usuario (solo para administradores)
@app.post("/register")
def register(user: schemas.UserRegister, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin_role)):
    # Verificar si el nombre ya está registrado
    db_user = db.query(models.User).filter(models.User.nombre == user.nombre).first()  # Aquí usamos 'nombre'
    if db_user:
        raise HTTPException(status_code=400, detail="Name already registered")

    # Hashear la contraseña
    hashed_password = services.hash_password(user.password)
    new_user = models.User(nombre=user.nombre, hashed_password=hashed_password, role=user.role)  # Usamos 'nombre' y 'hashed_password'
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

# Ruta para login (iniciar sesión)
@app.post("/login")
async def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    # Aquí usamos 'nombre' para la consulta
    db_user = db.query(models.User).filter(models.User.nombre == user.nombre).first()  # Usamos 'nombre'
    if db_user is None or not services.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Crear y devolver el token JWT
    access_token = services.create_access_token(data={"sub": db_user.nombre, "role": db_user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# Ruta para obtener información de la empresa (solo para admins o usuarios de la empresa)
@app.get("/company-info")
async def get_company_info(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.nombre == current_user.nombre).first()  # Usamos 'nombre'
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.role == "admin":
        # Si es admin, devolver toda la información de la empresa
        company_data = db.query(models.Company).all()
        return company_data
    elif db_user.role == "admin_empresa":
        # Si es admin_empresa, devolver solo la información de la empresa asociada al usuario
        company_data = db.query(models.Company).filter(models.Company.id == db_user.company_id).first()
        return company_data
    else:
        raise HTTPException(status_code=403, detail="Access denied for your role")

# Ruta para obtener información de usuario
@app.get("/user-info")
async def get_user_info(current_user: models.User = Depends(get_current_user)):
    return {"nombre": current_user.nombre, "role": current_user.role}  # Usamos 'nombre' en lugar de 'email'
