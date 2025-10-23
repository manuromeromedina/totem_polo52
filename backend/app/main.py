# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import SessionLocal
from app.routes.auth import router as auth_router
from app.routes.company_user import router as company_user_router
from app.routes.admin_users import router as admin_users_router
from app.routes.chat import router as chat_router
from app.routes.tipos import router as tipos
from app.routes.google_auth import router as google_auth_router

# ✨ IMPORTAR EL NUEVO ROUTER DE VOZ
from app.routes.voice import router as voice_router

from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware 
import os

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Totem Polo52 API",
    version="0.2.0",  # Actualizado por funcionalidad de voz
    description="API del Parque Industrial Polo 52 con Chatbot IA y funcionalidad de voz integrada"
)

# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARES (ORDEN IMPORTANTE)
# ═══════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════
# RUTAS
# ═══════════════════════════════════════════════════════════════════

# Incluir routers existentes
app.include_router(auth_router)
app.include_router(company_user_router)
app.include_router(admin_users_router)
app.include_router(chat_router)  # Chat de texto
app.include_router(tipos)
app.include_router(google_auth_router)

# ✨ INCLUIR EL ROUTER DE VOZ
app.include_router(voice_router)

# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS RAÍZ
# ═══════════════════════════════════════════════════════════════════

@app.get("/", tags=["root"])
def read_root():
    """
    Endpoint raíz con información de la API
    """
    return {
        "message": "Bienvenido al API Polo52",
        "version": "0.2.0",
        "features": {
            "auth": " Autenticación JWT",
            "chat": " Chatbot con IA (Gemini)",
            "voice": " Voz (Speech-to-Text y Text-to-Speech)",
            "users": " Gestión de usuarios y empresas",
            "google_auth": " Autenticación con Google"
        },
        "endpoints": {
            "docs": "/docs",
            "voice_status": "/api/voice/status",
            "voice_chat": "/api/voice/chat",
            "health": "/health"
        }
    }

@app.get("/health", tags=["health"])
def health_check():
    """
    Endpoint para verificar el estado de salud de la API
    """
    import app.services as services
    
    # Obtener estado de servicios de voz
    try:
        voice_status = services.get_voice_services_status()
        voice_provider = voice_status.get("provider", "none")
    except:
        voice_provider = "error"
    
    return {
        "status": "healthy",
        "api_version": "0.2.0",
        "services": {
            "database": " Connected",
            "gemini_ai": " Configured",
            "voice_provider": voice_provider if voice_provider else "⚠️ Not configured",
        },
        "timestamp": os.popen('date').read().strip()
    }

# ═══════════════════════════════════════════════════════════════════
# STARTUP EVENT (OPCIONAL)
# ═══════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """
    Evento que se ejecuta al iniciar la aplicación
    Muestra información de configuración
    """
    print("\n" + "="*70)
    print(" POLO 52 API - INICIANDO")
    print("="*70)
    print(f" Versión: 0.2.0")
    print(f" Entorno: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"  Base de datos: Configurada")
    print(f" Gemini AI: Configurado")
    
    # Verificar servicios de voz
    try:
        import app.services as services
        voice_status = services.get_voice_services_status()
        provider = voice_status.get("provider")
        
        if provider:
            print(f"🎤 Servicios de voz:  Activo ({provider})")
        else:
            print(f"🎤 Servicios de voz: ⚠️ No configurado")
            print(f"   💡 Configura GOOGLE_APPLICATION_CREDENTIALS")
    except Exception as e:
        print(f"🎤 Servicios de voz:  Error - {str(e)}")
    
    print("="*70)
    print(" API lista en: http://localhost:8000")
    print(" Documentación: http://localhost:8000/docs")
    print(" Estado de voz: http://localhost:8000/api/voice/status")
    print("="*70 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Evento que se ejecuta al cerrar la aplicación
    """
    print("\n" + "="*70)
    print(" POLO 52 API - CERRANDO")
    print("="*70 + "\n")
