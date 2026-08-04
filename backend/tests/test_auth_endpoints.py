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
    """
    remember_me viaja como campo del form (igual que username/password), NO
    como query param: así es como lo manda el frontend real. Un test previo
    lo mandaba por query y pasaba en falso, sin detectar que el frontend
    nunca llegaba a activar la cookie.
    """
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
        data={"username": "sofia", "password": "ClaveSegura1", "remember_me": "true"},
    )

    assert response.status_code == 200
    assert "remember_token" in response.cookies


def test_login_without_remember_me_does_not_set_cookie(auth_client):
    client, SessionLocal = auth_client
    db = SessionLocal()
    empresa = _add_company(db)
    user = _add_user(db, nombre="martina", email="martina@example.com", password="ClaveSegura1", empresa=empresa)
    role = _add_role(db)
    db.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    db.commit()
    db.close()

    response = client.post(
        "/login",
        data={"username": "martina", "password": "ClaveSegura1"},
    )

    assert response.status_code == 200
    assert "remember_token" not in response.cookies


def test_check_remember_restores_session_from_cookie(auth_client):
    """
    Flujo completo: login con remember_me -> el navegador se "cierra" (ya no
    manda el Bearer token) -> /check-remember debe restaurar la sesión
    usando únicamente la cookie remember_token.
    """
    client, SessionLocal = auth_client
    db = SessionLocal()
    empresa = _add_company(db)
    user = _add_user(db, nombre="lucia", email="lucia@example.com", password="ClaveSegura1", empresa=empresa)
    role = _add_role(db)
    db.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    db.commit()
    db.close()

    login_response = client.post(
        "/login",
        data={"username": "lucia", "password": "ClaveSegura1", "remember_me": "true"},
    )
    assert login_response.status_code == 200
    assert "remember_token" in login_response.cookies

    # La cookie se marca Secure (EXTERNAL_BASE_URL es https en el .env de
    # test), así que el jar automático del TestClient no la reenvía sobre su
    # base_url http://testserver. La adjuntamos a mano para simular lo que
    # un navegador real haría sobre HTTPS en producción.
    check_response = client.get(
        "/check-remember",
        cookies={"remember_token": login_response.cookies["remember_token"]},
    )
    body = check_response.json()

    assert check_response.status_code == 200
    assert body["logged_in"] is True
    assert body["user"]["nombre"] == "lucia"
    assert body["access_token"]


def test_check_remember_without_cookie_reports_not_logged_in(auth_client):
    client, SessionLocal = auth_client
    response = client.get("/check-remember")
    assert response.status_code == 200
    assert response.json() == {"logged_in": False}


def test_logout_clears_remember_cookie(auth_client):
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
        data={"username": "valentina", "password": "ClaveSegura1", "remember_me": "true"},
    )
    access_token = login_response.json()["access_token"]

    logout_response = client.post(
        "/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_response.status_code == 200

    # El cliente de test sigue mandando la cookie hasta que el server la
    # invalide explícitamente; verificamos que la respuesta de logout la
    # borre (Set-Cookie con expiración pasada / valor vacío).
    set_cookie_headers = logout_response.headers.get_list("set-cookie")
    assert any("remember_token=" in h and ("Max-Age=0" in h or "expires=" in h.lower()) for h in set_cookie_headers)
