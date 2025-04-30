from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:postgres@localhost/postgres"


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


import os

# Definir una clave secreta para JWT
SECRET_KEY = os.getenv("SECRET_KEY", "mi_clave_secreta_super_segura")
ALGORITHM = "HS256"
