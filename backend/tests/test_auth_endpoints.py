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
    # El conftest.py raiz pisa get_current_user globalmente (autouse) para el
    # resto de la suite; acá lo sacamos para ejercitar la validación real del
    # JWT (login/logout/etc contra la sqlite de este fixture).
    app.dependency_overrides.pop(auth_routes.get_current_user, None)
    auth_routes.reset_login_locks()
    client = TestClient(app)

    yield client, TestingSessionLocal

    auth_routes.reset_login_locks()
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
    assert payload["access_token"]


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


def test_logout_returns_ok_with_valid_token(auth_client):
    client, SessionLocal = auth_client
    db = SessionLocal()
    empresa = _add_company(db)
    user = _add_user(db, nombre="valentina", email="valentina@example.com", password="ClaveSegura1", empresa=empresa)
    role = _add_role(db)
    db.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    db.commit()
    db.close()

    login_response = client.post(
        "/login",
        data={"username": "valentina", "password": "ClaveSegura1"},
    )
    access_token = login_response.json()["access_token"]

    logout_response = client.post(
        "/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_response.status_code == 200


def test_logout_requires_valid_token(auth_client):
    client, SessionLocal = auth_client
    response = client.post("/logout", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def _usuario_con_rol(SessionLocal, nombre, *, empresa_estado=True, usuario_estado=True, cuil=1001):
    db = SessionLocal()
    empresa = _add_company(db, cuil=cuil, estado=empresa_estado)
    user = _add_user(db, nombre=nombre, email=f"{nombre}@example.com", password="ClaveSegura1", estado=usuario_estado, empresa=empresa)
    role = _add_role(db)
    db.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    db.commit()
    db.close()


def test_account_is_locked_after_5_failed_logins_even_with_the_right_password(auth_client):
    """Bloqueo por CUENTA en el servidor: no depende de la IP ni del navegador."""
    client, SessionLocal = auth_client
    _usuario_con_rol(SessionLocal, "lucia")
    for _ in range(5):
        assert client.post("/login", data={"username": "lucia", "password": "Incorrecta1"}).status_code == 401

    bloqueado = client.post("/login", data={"username": "lucia", "password": "ClaveSegura1"})
    assert bloqueado.status_code == 429
    assert "Retry-After" in bloqueado.headers

    auth_routes.reset_login_locks()  # pasado el bloqueo, la contraseña correcta vuelve a andar
    assert client.post("/login", data={"username": "lucia", "password": "ClaveSegura1"}).status_code == 200


def test_successful_login_resets_the_failure_count(auth_client):
    client, SessionLocal = auth_client
    _usuario_con_rol(SessionLocal, "martin")
    for _ in range(4):
        client.post("/login", data={"username": "martin", "password": "Incorrecta1"})
    assert client.post("/login", data={"username": "martin", "password": "ClaveSegura1"}).status_code == 200
    for _ in range(4):
        client.post("/login", data={"username": "martin", "password": "Incorrecta1"})
    assert client.post("/login", data={"username": "martin", "password": "ClaveSegura1"}).status_code == 200


def test_logout_revokes_the_token(auth_client):
    client, SessionLocal = auth_client
    _usuario_con_rol(SessionLocal, "sofia")
    token = client.post("/login", data={"username": "sofia", "password": "ClaveSegura1"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post("/logout", headers=headers).status_code == 200
    despues = client.post("/logout", headers=headers)
    assert despues.status_code == 401
    assert despues.json()["detail"] == "Sesión cerrada"

    # un login nuevo da un token distinto, que sí sirve
    nuevo = client.post("/login", data={"username": "sofia", "password": "ClaveSegura1"}).json()["access_token"]
    assert nuevo != token
    assert client.post("/logout", headers={"Authorization": f"Bearer {nuevo}"}).status_code == 200


def test_disabled_company_message_wins_over_disabled_user(auth_client):
    """Desactivar una empresa deshabilita a sus usuarios en cascada: el motivo que
    ve el usuario tiene que ser el de la empresa, no el de su cuenta."""
    client, SessionLocal = auth_client
    _usuario_con_rol(SessionLocal, "pedro", empresa_estado=False, usuario_estado=False)
    response = client.post("/login", data={"username": "pedro", "password": "ClaveSegura1"})
    assert response.status_code == 403
    assert "empresa asociada" in response.json()["detail"].lower()


def test_chat_endpoint_requires_a_session(auth_client):
    client, SessionLocal = auth_client
    assert client.post("/chat/", json={"message": "hola"}).status_code == 401
