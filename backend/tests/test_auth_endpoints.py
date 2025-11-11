from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app import models, services
from app.config import Base
from app.routes import auth as auth_routes


def _build_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return engine, TestingSessionLocal


def _add_role(db, tipo="publico"):
    role = models.Rol(tipo_rol=tipo)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def _add_company(db, *, cuil=1001, estado=True):
    empresa = models.Empresa(
        cuil=cuil,
        nombre="EmpresaTest",
        rubro="Logistica",
        cant_empleados=10,
        observaciones="",
        fecha_ingreso=date(2020, 1, 1),
        horario_trabajo="09 a 18",
        estado=estado,
    )
    db.add(empresa)
    db.commit()
    return empresa


def _add_user(db, *, nombre="usuario", email="user@example.com", password="Clave123!", estado=True, empresa=None):
    user = models.Usuario(
        nombre=nombre,
        email=email,
        contrasena=services.hash_password(password),
        estado=estado,
        fecha_registro=date.today(),
        cuil=empresa.cuil if empresa else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_client():
    engine, TestingSessionLocal = _build_test_db()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[auth_routes.get_db] = override_get_db
    client = TestClient(app)

    yield client, TestingSessionLocal

    app.dependency_overrides.pop(auth_routes.get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_login_with_username_returns_token(auth_client):
    client, SessionLocal = auth_client
    db = SessionLocal()
    empresa = _add_company(db)
    user = _add_user(db, nombre="juan", email="juan@example.com", password="ClaveSegura1", empresa=empresa)
    role = _add_role(db)
    db.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    db.commit()
    db.close()

    response = client.post(
        "/login",
        data={"username": "juan", "password": "ClaveSegura1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["tipo_rol"] == "publico"
    assert payload["remember_me"] is False


def test_login_fails_for_disabled_user(auth_client):
    client, SessionLocal = auth_client
    db = SessionLocal()
    empresa = _add_company(db)
    _add_user(db, nombre="ana", email="ana@example.com", password="ClaveSegura1", estado=False, empresa=empresa)
    db.close()

    response = client.post(
        "/login",
        data={"username": "ana", "password": "ClaveSegura1"},
    )

    assert response.status_code == 403
    assert "deshabilitada" in response.json()["detail"].lower()


def test_login_fails_when_empresa_desactivada(auth_client):
    client, SessionLocal = auth_client
    db = SessionLocal()
    empresa = _add_company(db, estado=False)
    _add_user(db, nombre="carlos", email="carlos@example.com", password="ClaveSegura1", empresa=empresa)
    db.close()

    response = client.post(
        "/login",
        data={"username": "carlos", "password": "ClaveSegura1"},
    )

    assert response.status_code == 403
    assert "empresa asociada" in response.json()["detail"].lower()


def test_login_with_remember_me_sets_cookie(auth_client):
    client, SessionLocal = auth_client
    db = SessionLocal()
    empresa = _add_company(db)
    user = _add_user(db, nombre="sofia", email="sofia@example.com", password="ClaveSegura1", empresa=empresa)
    role = _add_role(db)
    db.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    db.commit()
    db.close()

    response = client.post(
        "/login",
        params={"remember_me": True},
        data={"username": "sofia", "password": "ClaveSegura1"},
    )

    assert response.status_code == 200
    assert "remember_token" in response.cookies
