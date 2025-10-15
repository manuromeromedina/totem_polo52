# backend/tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importa tu FastAPI app y Base de modelos
from app.main import app
from app import models

# ----- DB de test (SQLite en memoria por defecto) -----
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if TEST_DATABASE_URL.startswith("sqlite") else {}
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)

def _get_db_override():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client(monkeypatch):
    # Override de dependencia get_db si existe en tu app
    try:
        from app.main import get_db
        app.dependency_overrides[get_db] = _get_db_override
    except Exception:
        pass

    # Mock SMTP para evitar envío de correos reales
    import smtplib
    class DummySMTP:
        def __init__(self, *a, **k): ...
        def sendmail(self, *a, **k): ...
        def quit(self): ...
        def __enter__(self): return self
        def __exit__(self, *exc): ...
    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}
