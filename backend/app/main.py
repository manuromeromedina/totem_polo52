# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import SessionLocal
from app.routes.auth import router as auth_router
from app.routes.company_user import router as company_user_router
from app.routes.admin_users import router as admin_users_router
from app.routes.chat import router as chat_router  # Importar el router de chat
from app.routes.tipos import router as tipos
from app.routes.google_auth import router as google_auth_router
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware 
import os


# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Totem Polo52 API",
    version="0.1.0",
)

# SessionMiddleware PRIMERO
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "fallback-secret-key")
)

# CORS DESPUÉS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "https://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# ─── RUTAS ────────────────────────────────────────────────────────────────────

# Incluir routers
app.include_router(auth_router)
app.include_router(company_user_router)
app.include_router(admin_users_router)
app.include_router(chat_router)  # Incluir el router del chat
app.include_router(tipos)
app.include_router(google_auth_router)

@app.get("/", tags=["root"])
def read_root():
    return {"message": "Bienvenido al API Polo52"}