# app/main.py
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app import models, schemas, services
from app.config import SessionLocal, SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    creds_exc = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate":"Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_name = payload.get("sub")
        if user_name is None:
            raise creds_exc
        user = db.query(models.User).filter(models.User.nombre == user_name).first()
        if not user:
            raise creds_exc
        return user
    except JWTError:
        raise creds_exc

def require_admin_role(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can register new users")
    return current_user

app = FastAPI()

@app.post("/register")
def register(dto: schemas.UserRegister, db: Session = Depends(get_db), 
             admin: models.User = Depends(require_admin_role)):
    if db.query(models.User).filter(models.User.nombre == dto.nombre).first():
        raise HTTPException(400, "Name already registered")
    user = models.User(
        nombre = dto.nombre,
        contrasena = services.hash_password(dto.password),
        # setea estado/fecha_registro/cuil si querés…
        role = dto.role
    )
    db.add(user)
    db.commit()
    return {"message":"User created"}

@app.post("/login")
def login(dto: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.nombre == dto.nombre).first()
    if not user or not services.verify_password(dto.password, user.contrasena):
        raise HTTPException(401, "Invalid credentials")
    token = services.create_access_token({"sub":user.nombre, "role":user.role})
    return {"access_token":token, "token_type":"bearer"}

# ... tus rutas /company-info, /user-info, etc.
