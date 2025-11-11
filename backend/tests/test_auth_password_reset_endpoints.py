from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, services
from app.config import Base
from app.main import app
from app.routes import auth as auth_routes


def _setup_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


@pytest.fixture
def reset_client():
    engine, SessionLocal = _setup_memory_db()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[auth_routes.get_db] = override_get_db
    client = TestClient(app)

    yield client, SessionLocal

    app.dependency_overrides.pop(auth_routes.get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _seed_user(session, *, email="user@example.com", estado=True):
    empresa = models.Empresa(
        cuil=10,
        nombre="Empresa Reset",
        rubro="Servicios",
        cant_empleados=20,
        observaciones="",
        fecha_ingreso=date(2020, 1, 1),
        horario_trabajo="08-18",
        estado=True,
    )
    session.add(empresa)
    session.commit()

    user = models.Usuario(
        nombre="usuario_reset",
        email=email,
        contrasena=services.hash_password("ClaveSegura1"),
        estado=estado,
        fecha_registro=date.today(),
        cuil=empresa.cuil,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def seeded_reset_client(reset_client):
    client, SessionLocal = reset_client
    session = SessionLocal()
    user = _seed_user(session)
    session.refresh(user)
    user_data = {"email": user.email, "nombre": user.nombre}
    session.close()
    return client, SessionLocal, user_data


def test_forgot_password_sends_email_when_user_active(seeded_reset_client):
    client, SessionLocal, user = seeded_reset_client

    with patch("smtplib.SMTP") as smtp_mock:
        response = client.post("/forgot-password", json={"email": user["email"]})

    assert response.status_code == 200
    assert "expires_in_minutes" in response.json()
    smtp_mock.assert_called()


def test_forgot_password_rejects_unknown_email(reset_client):
    client, *_ = reset_client
    response = client.post("/forgot-password", json={"email": "no@existe.com"})
    assert response.status_code == 404


def test_verify_reset_token_detects_disabled_user(reset_client):
    client, SessionLocal = reset_client
    session = SessionLocal()
    user = _seed_user(session, estado=False)
    token = services.create_password_reset_token(user.email, expires_minutes=5)
    session.close()

    response = client.post("/password-reset/verify-token", params={"token": token})
    payload = response.json()
    assert payload["valid"] is False
    assert payload["disabled"] is True


def test_forgot_password_confirm_success(seeded_reset_client):
    client, SessionLocal, user = seeded_reset_client
    token = services.create_password_reset_token(user["email"], expires_minutes=5)
    payload = {
        "token": token,
        "new_password": "NuevaClave1",
        "confirm_password": "NuevaClave1",
    }

    response = client.post("/forgot-password/confirm", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


def test_forgot_password_confirm_handles_used_token(seeded_reset_client):
    client, SessionLocal, user = seeded_reset_client
    token = services.create_password_reset_token(user["email"], expires_minutes=5)
    # Consumir token manualmente
    services.consume_password_reset_token(token)

    payload = {
        "token": token,
        "new_password": "NuevaClave1",
        "confirm_password": "NuevaClave1",
    }

    response = client.post("/forgot-password/confirm", json=payload)
    body = response.json()
    assert body["success"] is False
    assert body["used"] is True
