from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, services
from app.config import Base
from app.main import app
from app.routes import admin_users as admin_routes


POLO_TEST_CUIL = admin_routes.POLO_CUIL


def _setup_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


def _seed_admin_context(session):
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
    company = models.Empresa(
        cuil=1234,
        nombre="Empresa",
        rubro="Logística",
        cant_empleados=30,
        observaciones="",
        fecha_ingreso=date(2021, 5, 1),
        horario_trabajo="08-18",
        estado=True,
    )
    company_disabled = models.Empresa(
        cuil=1235,
        nombre="Empresa Off",
        rubro="Servicios",
        cant_empleados=15,
        observaciones="",
        fecha_ingreso=date(2022, 3, 1),
        horario_trabajo="07-17",
        estado=False,
    )
    tipo_servicio_polo = models.TipoServicioPolo(id_tipo_servicio_polo=1, tipo="Cowork")
    session.add(tipo_servicio_polo)
    session.commit()
    session.add_all([polo, company, company_disabled])
    session.commit()

    role_admin_polo = models.Rol(tipo_rol="admin_polo")
    role_admin_empresa = models.Rol(tipo_rol="admin_empresa")
    session.add_all([role_admin_polo, role_admin_empresa])
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
    session.add(models.RolUsuario(id_usuario=admin.id_usuario, id_rol=role_admin_polo.id_rol))
    session.commit()

    return {
        "admin_id": admin.id_usuario,
        "empresa_cuil": company.cuil,
        "empresa_disabled_cuil": company_disabled.cuil,
        "role_admin_empresa": role_admin_empresa.id_rol,
        "tipo_servicio_polo": tipo_servicio_polo.id_tipo_servicio_polo,
    }


@pytest.fixture
def admin_client():
    engine, SessionLocal = _setup_memory_db()
    session = SessionLocal()
    context = _seed_admin_context(session)
    session.close()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_require_admin():
        db = SessionLocal()
        user = db.query(models.Usuario).get(context["admin_id"])
        db.close()
        return user

    app.dependency_overrides[admin_routes.get_db] = override_get_db
    app.dependency_overrides[admin_routes.require_admin_polo] = override_require_admin
    app.dependency_overrides[admin_routes.get_current_user] = override_require_admin

    client = TestClient(app)
    yield client, SessionLocal, context
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_create_user_enforces_admin_empresa_limit(admin_client):
    client, SessionLocal, ctx = admin_client
    session = SessionLocal()
    # Crear usuarios admin_empresa hasta llegar al límite
    for idx in range(admin_routes.MAX_ADMIN_EMPRESA_PER_COMPANY):
        user = models.Usuario(
            nombre=f"emp{idx}",
            email=f"emp{idx}@test.com",
            contrasena=services.hash_password("Clave123!"),
            estado=True,
            fecha_registro=date.today(),
            cuil=ctx["empresa_cuil"],
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=ctx["role_admin_empresa"]))
        session.commit()
    session.close()

    response = client.post(
        "/usuarios",
        json={
            "nombre": "extra",
            "email": "extra@test.com",
            "cuil": ctx["empresa_cuil"],
            "id_rol": ctx["role_admin_empresa"],
            "estado": True,
        },
    )

    assert response.status_code == 400
    assert "máximo" in response.json()["detail"].lower()


def test_polo_details_endpoint_returns_data(admin_client):
    client, SessionLocal, ctx = admin_client
    response = client.get("/polo/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cuil"] == POLO_TEST_CUIL
    assert isinstance(payload["empresas"], list)


def test_toggle_company_state(admin_client):
    client, SessionLocal, ctx = admin_client
    deactivate = client.put(f"/empresas/{ctx['empresa_cuil']}/desactivar")
    assert deactivate.status_code == 200
    activate = client.put(f"/empresas/{ctx['empresa_cuil']}/activar")
    assert activate.status_code == 200


def test_create_and_list_companies(admin_client):
    client, SessionLocal, ctx = admin_client
    response = client.post(
        "/empresas",
        json={
            "cuil": 7777,
            "nombre": "Nueva",
            "rubro": "IT",
            "cant_empleados": 10,
            "fecha_ingreso": "2023-01-01",
            "horario_trabajo": "09-18",
            "estado": True,
        },
    )
    assert response.status_code == 200
    listado = client.get("/empresas")
    assert any(emp["cuil"] == 7777 for emp in listado.json())


def test_search_public_endpoints(admin_client):
    client, SessionLocal, ctx = admin_client
    session = SessionLocal()
    contacto = models.Contacto(
        cuil_empresa=ctx["empresa_cuil"],
        id_tipo_contacto=1,
        nombre="Contacto",
        telefono="123",
        datos={"email": "c@t.com"},
        direccion="Calle 1",
    )
    session.add(contacto)
    session.commit()
    session.close()

    resp = client.get("/search", params={"nombre": "Empresa"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    contactos = client.get("/search/contactos", params={"empresa": "Empresa"})
    assert contactos.status_code == 200
    assert len(contactos.json()) >= 1

    lotes = client.get("/search/lotes", params={"empresa": "Empresa"})
    assert lotes.status_code == 200
    assert len(lotes.json()) >= 0


def test_create_servicio_polo_and_lote(admin_client):
    client, SessionLocal, ctx = admin_client
    service_resp = client.post(
        "/serviciopolo",
        json={
            "nombre": "Cowork Este",
            "horario": "09-19",
            "datos": {"puestos": 10},
            "propietario": "Polo",
            "id_tipo_servicio_polo": ctx["tipo_servicio_polo"],
            "cuil": ctx["empresa_cuil"],
        },
    )
    assert service_resp.status_code == 200
    service_id = service_resp.json()["id_servicio_polo"]

    lote_resp = client.post(
        "/lotes",
        json={
            "dueno": "Empresa",
            "lote": 1,
            "manzana": 1,
            "id_servicio_polo": service_id,
        },
    )
    assert lote_resp.status_code == 200
    lots = client.get("/search/lotes", params={"nombre": "Empresa"})
    assert lots.status_code == 200
    assert len(lots.json()) >= 1


def test_list_endpoints_return_data(admin_client):
    client, SessionLocal, ctx = admin_client
    assert client.get("/usuarios").status_code == 200
    assert client.get("/serviciopolo").status_code == 200
    assert client.get("/lotes").status_code == 200
    all_resp = client.get("/all")
    assert all_resp.status_code == 200


def test_users_limits_status(admin_client):
    client, SessionLocal, ctx = admin_client
    session = SessionLocal()
    data = admin_routes.get_users_limits_status(db=session)
    session.close()
    assert "polo_info" in data
    assert data["limites_configurados"]["polo_cuil"] == POLO_TEST_CUIL


def test_change_password_request(admin_client, monkeypatch):
    client, SessionLocal, ctx = admin_client

    monkeypatch.setattr(services, "create_password_reset_token", lambda email: "token123")

    called = {}

    def fake_send(*args, **kwargs):
        called["sent"] = True
        return True

    monkeypatch.setattr(services, "send_password_change_notification", fake_send)

    class DummySMTP:
        def __init__(self, *args, **kwargs):
            pass
        def starttls(self):
            pass
        def login(self, *args, **kwargs):
            pass
        def send_message(self, *args, **kwargs):
            called["smtp"] = True
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            pass

    import types, sys
    monkeypatch.setitem(sys.modules, "smtplib", types.SimpleNamespace(SMTP=DummySMTP))

    response = client.post("/polo/change-password-request")
    assert response.status_code == 200
    assert called.get("smtp") is True


def test_list_roles_and_get_user(admin_client):
    client, SessionLocal, ctx = admin_client
    roles_resp = client.get("/roles")
    assert roles_resp.status_code == 200
    assert len(roles_resp.json()) >= 1

    admin_id = ctx["admin_id"]
    user_resp = client.get(f"/usuarios/{admin_id}")
    assert user_resp.status_code == 200
    assert user_resp.json()["email"].startswith("admin@")
