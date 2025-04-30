from fastapi import FastAPI
from app.routes import auth, users, company
from app.config import engine
from app.models import Base

# Inicialización de la app
app = FastAPI()

# Iniciamos la base de datos (conexión)
Base.metadata.create_all(bind=engine)

# Rutas
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(company.router)
