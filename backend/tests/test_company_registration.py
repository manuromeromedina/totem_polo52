from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, services
from app.config import Base, get_db
from app.main import app
from app.rate_limit import reset_rate_limits


def _setup_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


def _seed_roles(session):
    for tipo in ("admin_polo", "admin_empresa", "publico"):
        session.add(models.Rol(tipo_rol=tipo))
    session.commit()


@pytest.fixture
def registration_client():
    engine, SessionLocal = _setup_memory_db()
    session = SessionLocal()
    _seed_roles(session)
    session.close()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    reset_rate_limits()

    client = TestClient(app)
    yield client, SessionLocal
    app.dependency_overrides.clear()
    reset_rate_limits()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


VALID_PAYLOAD = {
    "cuil": 30000000001,
    "nombre": "Empresa Nueva SA",
    "rubro": "Tecnología",
    "cant_empleados": 12,
    "horario_trabajo": "09-18",
    "usuario_nombre": "empresanueva",
    "email": "empresanueva@test.com",
    "password": "Clave123!",
}


def _login(client, nombre=VALID_PAYLOAD["usuario_nombre"], password=VALID_PAYLOAD["password"]):
    return client.post("/login", data={"username": nombre, "password": password})


def test_register_creates_pending_empresa_y_usuario(registration_client, monkeypatch):
    client, SessionLocal = registration_client
    monkeypatch.setattr(services, "send_registration_received_email", lambda **kwargs: True)

    resp = client.post("/register", json=VALID_PAYLOAD)
    assert resp.status_code == 200

    session = SessionLocal()
    empresa = session.query(models.Empresa).filter(models.Empresa.cuil == VALID_PAYLOAD["cuil"]).first()
    assert empresa is not None
    assert empresa.estado is False
    assert empresa.estado_solicitud == "pendiente"

    usuario = (
        session.query(models.Usuario)
        .filter(models.Usuario.nombre == VALID_PAYLOAD["usuario_nombre"])
        .first()
    )
    assert usuario is not None
    assert usuario.mostrar_bienvenida is True
    roles = [r.tipo_rol for r in usuario.roles]
    assert roles == ["admin_empresa"]
    session.close()


def test_register_rejects_duplicate_cuil(registration_client, monkeypatch):
    client, _ = registration_client
    monkeypatch.setattr(services, "send_registration_received_email", lambda **kwargs: True)

    assert client.post("/register", json=VALID_PAYLOAD).status_code == 200

    dup_payload = {**VALID_PAYLOAD, "usuario_nombre": "otronombre", "email": "otro@test.com"}
    second = client.post("/register", json=dup_payload)
    assert second.status_code == 400
    assert "cuil" in second.json()["detail"].lower()


def test_register_rejects_duplicate_username_and_email(registration_client, monkeypatch):
    client, _ = registration_client
    monkeypatch.setattr(services, "send_registration_received_email", lambda **kwargs: True)

    assert client.post("/register", json=VALID_PAYLOAD).status_code == 200

    dup_nombre = {**VALID_PAYLOAD, "cuil": 30000000002, "email": "otro@test.com"}
    resp = client.post("/register", json=dup_nombre)
    assert resp.status_code == 400
    assert "nombre" in resp.json()["detail"].lower()

    dup_email = {**VALID_PAYLOAD, "cuil": 30000000003, "usuario_nombre": "otronombre"}
    resp = client.post("/register", json=dup_email)
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


def test_login_blocked_while_pending(registration_client, monkeypatch):
    client, _ = registration_client
    monkeypatch.setattr(services, "send_registration_received_email", lambda **kwargs: True)
    client.post("/register", json=VALID_PAYLOAD)

    resp = _login(client)
    assert resp.status_code == 403
    assert "pendiente de aprobación" in resp.json()["detail"].lower()


def test_login_works_after_approval_and_returns_welcome_flag(registration_client, monkeypatch):
    client, SessionLocal = registration_client
    monkeypatch.setattr(services, "send_registration_received_email", lambda **kwargs: True)
    client.post("/register", json=VALID_PAYLOAD)

    session = SessionLocal()
    empresa = session.query(models.Empresa).filter(models.Empresa.cuil == VALID_PAYLOAD["cuil"]).first()
    empresa.estado = True
    empresa.estado_solicitud = "aprobada"
    session.commit()
    session.close()

    resp = _login(client)
    assert resp.status_code == 200
    assert resp.json()["mostrar_bienvenida"] is True


def test_login_blocked_with_rejected_message(registration_client, monkeypatch):
    client, SessionLocal = registration_client
    monkeypatch.setattr(services, "send_registration_received_email", lambda **kwargs: True)
    client.post("/register", json=VALID_PAYLOAD)

    session = SessionLocal()
    empresa = session.query(models.Empresa).filter(models.Empresa.cuil == VALID_PAYLOAD["cuil"]).first()
    empresa.estado_solicitud = "rechazada"
    session.commit()
    session.close()

    resp = _login(client)
    assert resp.status_code == 403
    assert "rechazada" in resp.json()["detail"].lower()


def test_bienvenida_vista_marks_flag_false(registration_client, monkeypatch):
    client, SessionLocal = registration_client
    monkeypatch.setattr(services, "send_registration_received_email", lambda **kwargs: True)
    client.post("/register", json=VALID_PAYLOAD)

    session = SessionLocal()
    empresa = session.query(models.Empresa).filter(models.Empresa.cuil == VALID_PAYLOAD["cuil"]).first()
    empresa.estado = True
    empresa.estado_solicitud = "aprobada"
    session.commit()
    session.close()

    token = _login(client).json()["access_token"]
    resp = client.post("/bienvenida-vista", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    session = SessionLocal()
    usuario = (
        session.query(models.Usuario)
        .filter(models.Usuario.nombre == VALID_PAYLOAD["usuario_nombre"])
        .first()
    )
    assert usuario.mostrar_bienvenida is False
    session.close()
