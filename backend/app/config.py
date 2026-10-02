#app/config.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv


load_dotenv()

class Settings:
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")

settings = Settings()

# Obtener la URL de la base de datos desde las variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL")

# Validar que DATABASE_URL esté definida
if not DATABASE_URL:
    raise ValueError(
        "No se encontró DATABASE_URL. Asegúrate de definirla en el archivo .env o como variable de entorno."
    )



# pool_pre_ping: el pooler de Supabase corta conexiones inactivas; sin el ping,
# la primera query sobre una conexión ya cerrada revienta con 500 intermitentes.
# pool_recycle las renueva antes de que el servidor las corte.
engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- nuevo ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# --- fin ---

SECRET_KEY = os.getenv("SECRET_KEY", "mi_clave_super_secreta")
ALGORITHM = "HS256"