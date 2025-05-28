# app/main.py
from fastapi import FastAPI
from app.config import SessionLocal
from app.routes.auth import router as auth_router  # Importar el router de auth
from app.routes.company_user import router as company_user_router  # Importar el router de company_user
from app.routes.admin_users import router as admin_users_router  # Importar el router de admin_users
from app.routes.public import router as public_router  # Importar el router de public

app = FastAPI(
    title="Totem Polo52 API",
    version="0.1.0",
)

# ─── RUTAS ────────────────────────────────────────────────────────────────────

# Incluir routers
app.include_router(auth_router)
app.include_router(company_user_router)
app.include_router(admin_users_router)
app.include_router(public_router)

@app.get("/", tags=["root"])
def read_root():
    return {"message": "Bienvenido al API Polo52"}