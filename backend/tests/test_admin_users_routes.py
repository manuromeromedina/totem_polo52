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


def test_create_user_rejects_admin_empresa_role(admin_client):
    """admin_empresa ya no se crea a mano desde /usuarios: se crea (junto con
    su empresa) por el autoregistro público y su aprobación por admin_polo."""
    client, SessionLocal, ctx = admin_client

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
    assert "registro público" in response.json()["detail"].lower()


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


def _add_empresa_user(SessionLocal, cuil, nombre):
    session = SessionLocal()
    session.add(models.Usuario(
        nombre=nombre,
        email=f"{nombre}@test.com",
        contrasena=services.hash_password("Clave123!"),
        estado=True,
        fecha_registro=date.today(),
        cuil=cuil,
    ))
    session.commit()
    session.close()


def _estados(SessionLocal, cuil, nombre_usuario):
    session = SessionLocal()
    emp = session.query(models.Empresa).filter(models.Empresa.cuil == cuil).first()
    user = session.query(models.Usuario).filter(models.Usuario.nombre == nombre_usuario).first()
    result = (emp.estado, user.estado)
    session.close()
    return result


def test_update_company_estado_propagates_to_users(admin_client):
    """Desactivar/activar desde el formulario de edición (PUT) tiene que
    propagar el estado igual que /desactivar y /activar."""
    client, SessionLocal, ctx = admin_client
    _add_empresa_user(SessionLocal, ctx["empresa_cuil"], "empleado")

    off = client.put(f"/empresas/{ctx['empresa_cuil']}", json={"estado": False})
    assert off.status_code == 200
    assert _estados(SessionLocal, ctx["empresa_cuil"], "empleado") == (False, False)

    on = client.put(f"/empresas/{ctx['empresa_cuil']}", json={"estado": True})
    assert on.status_code == 200
    assert _estados(SessionLocal, ctx["empresa_cuil"], "empleado") == (True, True)


@pytest.mark.parametrize("solicitud", ["pendiente", "rechazada"])
def test_update_company_cannot_activate_unapproved_request(admin_client, solicitud):
    client, SessionLocal, ctx = admin_client
    session = SessionLocal()
    emp = session.query(models.Empresa).filter(models.Empresa.cuil == ctx["empresa_disabled_cuil"]).first()
    emp.estado_solicitud = solicitud
    session.commit()
    session.close()
    _add_empresa_user(SessionLocal, ctx["empresa_disabled_cuil"], "solicitante")

    for path in (f"/empresas/{ctx['empresa_disabled_cuil']}", f"/empresas/{ctx['empresa_disabled_cuil']}/activar"):
        response = client.put(path, json={"estado": True}) if not path.endswith("activar") else client.put(path)
        assert response.status_code == 400
        assert "Aprobala desde Solicitudes" in response.json()["detail"]
    assert _estados(SessionLocal, ctx["empresa_disabled_cuil"], "solicitante")[0] is False


def test_update_company_without_estado_keeps_users_untouched(admin_client):
    client, SessionLocal, ctx = admin_client
    _add_empresa_user(SessionLocal, ctx["empresa_cuil"], "empleado2")

    response = client.put(f"/empresas/{ctx['empresa_cuil']}", json={"rubro": "Otro rubro"})
    assert response.status_code == 200
    assert response.json()["rubro"] == "Otro rubro"
    assert _estados(SessionLocal, ctx["empresa_cuil"], "empleado2") == (True, True)


def test_list_companies(admin_client):
    client, SessionLocal, ctx = admin_client
    listado = client.get("/empresas")
    assert listado.status_code == 200
    assert any(emp["cuil"] == ctx["empresa_cuil"] for emp in listado.json())


def test_solicitudes_registro_approve_and_reject(admin_client, monkeypatch):
    client, SessionLocal, ctx = admin_client
    monkeypatch.setattr(services, "send_registration_approved_email", lambda **kwargs: True)
    monkeypatch.setattr(services, "send_registration_rejected_email", lambda **kwargs: True)

    session = SessionLocal()
    pendiente = models.Empresa(
        cuil=9999,
        nombre="Pendiente SA",
        rubro="Comercio",
        cant_empleados=5,
        observaciones="",
        fecha_ingreso=date.today(),
        horario_trabajo="09-18",
        estado=False,
        estado_solicitud="pendiente",
    )
    session.add(pendiente)
    session.commit()
    usuario = models.Usuario(
        nombre="pendiente_admin",
        email="pendiente@test.com",
        contrasena=services.hash_password("Clave123!"),
        estado=True,
        fecha_registro=date.today(),
        cuil=pendiente.cuil,
    )
    session.add(usuario)
    session.commit()
    session.close()

    solicitudes = client.get("/empresas/solicitudes")
    assert solicitudes.status_code == 200
    assert any(s["cuil"] == 9999 for s in solicitudes.json())

    rechazo = client.post("/empresas/9999/rechazar")
    assert rechazo.status_code == 200
    session = SessionLocal()
    emp = session.query(models.Empresa).filter(models.Empresa.cuil == 9999).first()
    assert emp.estado_solicitud == "rechazada"
    assert emp.estado is False
    session.close()

    aprobar = client.post("/empresas/9999/aprobar")
    assert aprobar.status_code == 200
    session = SessionLocal()
    emp = session.query(models.Empresa).filter(models.Empresa.cuil == 9999).first()
    assert emp.estado_solicitud == "aprobada"
    assert emp.estado is True
    session.close()


def test_public_listings_hide_internal_contacts_and_unapproved_companies(admin_client):
    """El directorio y las búsquedas los ve cualquier usuario logueado: solo
    pueden mostrar contactos comerciales y empresas activas y aprobadas."""
    client, SessionLocal, ctx = admin_client
    session = SessionLocal()
    session.add_all([models.TipoContacto(id_tipo_contacto=1, tipo="comercial"), models.TipoContacto(id_tipo_contacto=2, tipo="empresarial")])
    session.add(models.Empresa(cuil=7777, nombre="Empresa Pendiente", rubro="X", cant_empleados=1, observaciones="",
                               fecha_ingreso=date.today(), horario_trabajo="x", estado=True, estado_solicitud="pendiente"))
    session.commit()
    session.add_all([
        models.Contacto(cuil_empresa=ctx["empresa_cuil"], id_tipo_contacto=1, nombre="Ventas", telefono="111", datos={}, direccion="A"),
        models.Contacto(cuil_empresa=ctx["empresa_cuil"], id_tipo_contacto=2, nombre="Gerencia interna", telefono="999", datos={}, direccion="B"),
        models.Contacto(cuil_empresa=7777, id_tipo_contacto=1, nombre="Ventas pendiente", telefono="777", datos={}, direccion="C"),
    ])
    session.commit()
    session.close()

    directorio = client.get("/empresas/directorio").json()
    empresa = next(e for e in directorio if e["cuil"] == ctx["empresa_cuil"])
    assert [c["nombre"] for c in empresa["contactos"]] == ["Ventas"]
    assert all(e["cuil"] != 7777 for e in directorio)

    contactos = client.get("/search/contactos").json()
    nombres = {c["nombre"] for c in contactos}
    assert "Ventas" in nombres
    assert "Gerencia interna" not in nombres
    assert "Ventas pendiente" not in nombres

    busqueda = client.get("/search", params={"name": "Pendiente"})
    assert busqueda.status_code == 404


def test_search_public_endpoints(admin_client):
    client, SessionLocal, ctx = admin_client
    session = SessionLocal()
    session.add_all([models.TipoContacto(id_tipo_contacto=1, tipo="comercial"), models.TipoContacto(id_tipo_contacto=2, tipo="empresarial")])
    session.commit()
    session.add_all([
        models.Contacto(cuil_empresa=ctx["empresa_cuil"], id_tipo_contacto=1, nombre="Contacto",
                        telefono="123", datos={"email": "c@t.com"}, direccion="Calle 1"),
        models.Contacto(cuil_empresa=ctx["empresa_cuil"], id_tipo_contacto=2, nombre="Gerencia interna",
                        telefono="999", datos={}, direccion="Interna"),
    ])
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


def test_create_servicio_polo_rejects_unknown_cuil_and_tipo(admin_client):
    client, SessionLocal, ctx = admin_client
    base = {"nombre": "X", "datos": {"m2": 10}, "id_tipo_servicio_polo": ctx["tipo_servicio_polo"], "cuil": 999999}

    sin_empresa = client.post("/serviciopolo", json=base)
    assert sin_empresa.status_code == 400
    assert "No existe una empresa registrada con CUIL 999999" in sin_empresa.json()["detail"]

    tipo_invalido = client.post("/serviciopolo", json={**base, "cuil": ctx["empresa_cuil"], "id_tipo_servicio_polo": 999})
    assert tipo_invalido.status_code == 400


@pytest.mark.parametrize("id_servicio_polo", [None, 999999])
def test_create_lote_rejects_missing_or_unknown_servicio(admin_client, id_servicio_polo):
    client, SessionLocal, ctx = admin_client
    body = {"dueno": "Empresa", "lote": 1, "manzana": 1}
    if id_servicio_polo is not None:
        body["id_servicio_polo"] = id_servicio_polo
    response = client.post("/lotes", json=body)
    assert response.status_code == 400
    assert response.json()["detail"] == "El servicio del polo indicado no existe"


def test_unhandled_error_returns_json_500_with_cors_headers(admin_client):
    """Un error inesperado tiene que llegar al front como 500 (con CORS), no
    como una respuesta bloqueada por el navegador ("Error de conexión")."""
    client, SessionLocal, ctx = admin_client

    def broken_db():
        raise RuntimeError("la base explotó")
        yield  # pragma: no cover

    app.dependency_overrides[admin_routes.get_db] = broken_db
    response = client.get("/empresas", headers={"Origin": "http://localhost:4200"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno del servidor. Intentá de nuevo en unos minutos."}
    assert response.headers.get("access-control-allow-origin") == "http://localhost:4200"
    assert response.headers.get("x-content-type-options") == "nosniff"


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
    all_resp = client.get("/empresas/directorio")
    assert all_resp.status_code == 200


def test_change_password_request(admin_client, monkeypatch):
    client, SessionLocal, ctx = admin_client

    monkeypatch.setattr(services, "create_password_reset_token", lambda email: "token123")

    called = {}

    def fake_send(*, email, nombre, reset_link):
        called["email"] = email
        called["reset_link"] = reset_link
        return True

    monkeypatch.setattr(services, "send_admin_password_change_request_email", fake_send)

    response = client.post("/polo/change-password-request")
    assert response.status_code == 200
    assert called.get("reset_link", "").endswith("token123")


def test_change_password_request_fails_when_email_not_sent(admin_client, monkeypatch):
    client, SessionLocal, ctx = admin_client

    monkeypatch.setattr(services, "create_password_reset_token", lambda email: "token123")
    monkeypatch.setattr(services, "send_admin_password_change_request_email", lambda **kwargs: False)

    response = client.post("/polo/change-password-request")
    assert response.status_code == 500


def test_list_roles_and_get_user(admin_client):
    client, SessionLocal, ctx = admin_client
    roles_resp = client.get("/roles")
    assert roles_resp.status_code == 200
    assert len(roles_resp.json()) >= 1

    admin_id = ctx["admin_id"]
    user_resp = client.get(f"/usuarios/{admin_id}")
    assert user_resp.status_code == 200
    assert user_resp.json()["email"].startswith("admin@")
