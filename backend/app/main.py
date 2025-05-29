# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import SessionLocal
from app.routes.auth import router as auth_router
from app.routes.company_user import router as company_user_router
from app.routes.admin_users import router as admin_users_router
from app.routes.public import router as public_router
from app.routes.chat import router as chat_router  # Importar el router de chat
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Totem Polo52 API",
    version="0.1.0",
)

# Configurar CORS para permitir solicitudes desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # URL de tu frontend Angular
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── RUTAS ────────────────────────────────────────────────────────────────────

# Incluir routers
app.include_router(auth_router)
app.include_router(company_user_router)
app.include_router(admin_users_router)
app.include_router(public_router)
app.include_router(chat_router)  # Incluir el router del chat

@app.get("/", tags=["root"])
def read_root():
    return {"message": "Bienvenido al API Polo52"}