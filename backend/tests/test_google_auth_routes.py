from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, services
from app.config import Base
from app.main import app
from app.routes import google_auth as google_routes
from app.routes import auth as auth_routes


def _setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


@pytest.fixture
def google_client():
    engine, SessionLocal = _setup_db()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    class DummyAdmin:
        pass

    app.dependency_overrides[auth_routes.get_db] = override_get_db
    app.dependency_overrides[google_routes.require_admin_polo] = lambda: DummyAdmin()

    client = TestClient(app)
    yield client, SessionLocal
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


POLO_TEST_CUIL = 44123456789


def _seed_google_base(SessionLocal):
    session = SessionLocal()
    empresa_activa = models.Empresa(
        cuil=1234,
        nombre="Empresa",
        rubro="Logística",
        cant_empleados=20,
        observaciones="",
        fecha_ingreso=date(2021, 1, 1),
        horario_trabajo="08-18",
        estado=True,
    )
    empresa_inactiva = models.Empresa(
        cuil=1235,
        nombre="Empresa Inactiva",
        rubro="Servicios",
        cant_empleados=10,
        observaciones="",
        fecha_ingreso=date(2022, 5, 1),
        horario_trabajo="07-15",
        estado=False,
    )
    polo = models.Empresa(
        cuil=POLO_TEST_CUIL,
        nombre="Polo",
        rubro="Administración",
        cant_empleados=10,
        observaciones="",
        fecha_ingreso=date(2020, 1, 1),
        horario_trabajo="08-16",
        estado=True,
    )
    session.add_all([empresa_activa, empresa_inactiva, polo])
    session.commit()

    role_admin = models.Rol(tipo_rol="admin_polo")
    role_public = models.Rol(tipo_rol="publico")
    session.add_all([role_admin, role_public])
    session.commit()
    admin = models.Usuario(
        nombre="admin",
        email="admin@polo.com",
        contrasena=services.hash_password("Clave123!"),
        estado=True,
        fecha_registro=date.today(),
        cuil=polo.cuil,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    session.add(models.RolUsuario(id_usuario=admin.id_usuario, id_rol=role_admin.id_rol))
    session.commit()
    info = {
        "active_cuil": empresa_activa.cuil,
        "inactive_cuil": empresa_inactiva.cuil,
        "public_role": role_public.id_rol,
    }
    session.close()
    return info


def _create_user(session, *, email, cuil, role_id, estado=True):
    user = models.Usuario(
        nombre=email.split("@")[0],
        email=email,
        contrasena=services.hash_password("Clave123!"),
        estado=estado,
        fecha_registro=date.today(),
        cuil=cuil,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role_id))
    session.commit()
    return user


async def _mock_authorize_access_token(*args, **kwargs):
    return {"userinfo": {"email": "user@example.com", "name": "User"}}


def test_google_callback_user_not_found(monkeypatch, google_client):
    client, SessionLocal = google_client
    _seed_google_base(SessionLocal)

    async_mock = AsyncMock(side_effect=_mock_authorize_access_token)
    monkeypatch.setattr(google_routes.oauth.google, "authorize_access_token", async_mock)

    response = client.get("/auth/google/callback", follow_redirects=False)
    assert response.status_code == 307
    assert "pending" in response.headers["location"]


def test_google_callback_user_disabled(monkeypatch, google_client):
    client, SessionLocal = google_client
    data = _seed_google_base(SessionLocal)
    session = SessionLocal()
    _create_user(
        session,
        email="user@example.com",
        cuil=data["active_cuil"],
        role_id=data["public_role"],
        estado=False,
    )
    session.close()

    async_mock = AsyncMock(side_effect=_mock_authorize_access_token)
    monkeypatch.setattr(google_routes.oauth.google, "authorize_access_token", async_mock)

    response = client.get("/auth/google/callback", follow_redirects=False)
    assert response.status_code == 307
    assert "usuario_inhabilitado" in response.headers["location"]


def test_google_callback_company_disabled(monkeypatch, google_client):
    client, SessionLocal = google_client
    data = _seed_google_base(SessionLocal)
    session = SessionLocal()
    _create_user(
        session,
        email="user@example.com",
        cuil=data["inactive_cuil"],
        role_id=data["public_role"],
        estado=True,
    )
    session.close()

    async_mock = AsyncMock(side_effect=_mock_authorize_access_token)
    monkeypatch.setattr(google_routes.oauth.google, "authorize_access_token", async_mock)

    response = client.get("/auth/google/callback", follow_redirects=False)
    assert response.status_code == 307
    assert "empresa_desactivada" in response.headers["location"]


def test_google_callback_user_success(monkeypatch, google_client):
    client, SessionLocal = google_client
    data = _seed_google_base(SessionLocal)
    session = SessionLocal()
    _create_user(
        session,
        email="user@example.com",
        cuil=data["active_cuil"],
        role_id=data["public_role"],
        estado=True,
    )
    session.close()

    async_mock = AsyncMock(side_effect=_mock_authorize_access_token)
    monkeypatch.setattr(google_routes.oauth.google, "authorize_access_token", async_mock)
    monkeypatch.setattr(services, "create_access_token", lambda data: "token123")

    response = client.get("/auth/google/callback", follow_redirects=False)
    assert response.status_code == 307
    assert "token=token123" in response.headers["location"]


def test_register_pending_google_user_happy_path(monkeypatch, google_client):
    client, SessionLocal = google_client
    data = _seed_google_base(SessionLocal)
    session = SessionLocal()
    empresa = session.query(models.Empresa).filter(models.Empresa.cuil == data["active_cuil"]).first()
    rol = session.query(models.Rol).filter(models.Rol.tipo_rol == "publico").first()
    session.close()

    response = client.post(
        "/auth/google/register-pending",
        params={
            "email": "nuevo@empresa.com",
            "name": "Nuevo",
            "cuil": empresa.cuil,
            "id_rol": rol.id_rol,
        },
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith("Usuario registrado")


def test_google_logout_returns_static_message(google_client):
    client, _ = google_client
    response = client.post("/auth/google/logout-google")
    assert response.status_code == 200
    payload = response.json()
    assert "accounts.google.com" in payload["google_logout_url"]
