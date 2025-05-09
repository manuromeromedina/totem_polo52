# app/config.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/postgres"
)

engine = create_engine(DATABASE_URL, echo=True)
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
