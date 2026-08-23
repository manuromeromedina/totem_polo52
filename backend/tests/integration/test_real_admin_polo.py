"""
Tests de integracion reales (contra Supabase, con rollback) para las rutas
de admin_polo: perfil del Polo, info comercial del Polo, empresas, usuarios,
servicios del Polo y lotes.
"""
import pytest

from app import models
from app.routes import admin_users as admin_routes
from tests.integration.conftest import (
    requires_real_db,
    fake_cuil,
    create_empresa,
    create_user,
    login,
    auth_headers,
    get_or_create_role,
)


@pytest.fixture(autouse=True)
def mute_emails(monkeypatch):
    for fn_name in (
        "send_welcome_email",
        "send_registration_approved_email",
        "send_registration_rejected_email",
    ):
        monkeypatch.setattr(admin_routes.services, fn_name, lambda *a, **k: True)
    yield


def _admin_polo_client(real_client):
    """Crea un usuario admin_polo real (ligado a la empresa Polo real) y
    devuelve (client, session, token, polo_empresa)."""
    client, session = real_client
    polo_empresa = (
        session.query(models.Empresa).filter_by(cuil=admin_routes.POLO_CUIL).first()
    )
    assert polo_empresa is not None, "La empresa del Polo debe existir en produccion"
    user, password = create_user(session, empresa=polo_empresa, rol_tipo="admin_polo")
    token = login(client, user.nombre, password)
    return client, session, token, polo_empresa


# ───────────────────────── /polo/me ─────────────────────────

@requires_real_db
def test_get_polo_me_returns_real_data(real_client):
    client, session, token, polo_empresa = _admin_polo_client(real_client)
    response = client.get("/polo/me", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["cuil"] == polo_empresa.cuil
    assert isinstance(body["empresas"], list)
    assert isinstance(body["usuarios"], list)


@requires_real_db
def test_update_polo_me_persists_within_transaction(real_client):
    client, session, token, polo_empresa = _admin_polo_client(real_client)
    response = client.put(
        "/polo/me",
        json={"cant_empleados": 8, "observaciones": "obs de test", "horario_trabajo": "8 a 20"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["horario_trabajo"] == "8 a 20"


@requires_real_db
def test_polo_routes_reject_non_admin_polo_user(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.get("/polo/me", headers=auth_headers(token))
    assert response.status_code == 403


# ───────────────────────── /polo/comercial ─────────────────────────

@requires_real_db
def test_polo_comercial_upsert_creates_and_marks_completado(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)

    response = client.put(
        "/polo/comercial",
        json={"productos_servicios": "Naves industriales de test", "publico_objetivo": "B2B"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["completado"] is True
    assert body["productos_servicios"] == "Naves industriales de test"

    read_response = client.get("/polo/comercial", headers=auth_headers(token))
    assert read_response.status_code == 200
    assert read_response.json()["productos_servicios"] == "Naves industriales de test"


# ───────────────────────── /empresas ─────────────────────────

@requires_real_db
def test_admin_update_empresa_nombre_rubro(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    empresa = create_empresa(session, nombre="Nombre Original")

    response = client.put(
        f"/empresas/{empresa.cuil}",
        json={"nombre": "Nombre Editado", "rubro": None, "estado": None, "cant_empleados": None, "observaciones": None, "horario_trabajo": None},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["nombre"] == "Nombre Editado"


@requires_real_db
def test_desactivar_y_activar_empresa_propaga_a_usuarios(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    empresa = create_empresa(session)
    user, _password = create_user(session, empresa=empresa, rol_tipo="admin_empresa")

    desactivar_resp = client.put(f"/empresas/{empresa.cuil}/desactivar", headers=auth_headers(token))
    assert desactivar_resp.status_code == 200
    session.refresh(empresa)
    session.refresh(user)
    assert empresa.estado is False
    assert user.estado is False

    activar_resp = client.put(f"/empresas/{empresa.cuil}/activar", headers=auth_headers(token))
    assert activar_resp.status_code == 200
    session.refresh(empresa)
    session.refresh(user)
    assert empresa.estado is True
    assert user.estado is True


@requires_real_db
def test_empresa_actions_404_for_unknown_cuil(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    response = client.put(f"/empresas/{fake_cuil()}/desactivar", headers=auth_headers(token))
    assert response.status_code == 404


# ───────────────────────── solicitudes de registro ─────────────────────────

@requires_real_db
def test_solicitudes_pendientes_flow_aprobar(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    cuil = fake_cuil()

    register_resp = client.post(
        "/register",
        json={
            "cuil": cuil,
            "nombre": "Empresa Pendiente Test",
            "rubro": "Testing",
            "cant_empleados": 2,
            "horario_trabajo": "9 a 18",
            "usuario_nombre": f"pend_user_{cuil}",
            "email": f"pend_{cuil}@example.com",
            "password": "ClaveSegura1",
        },
    )
    assert register_resp.status_code == 200

    solicitudes = client.get("/empresas/solicitudes", headers=auth_headers(token))
    assert solicitudes.status_code == 200
    assert any(s["cuil"] == cuil for s in solicitudes.json())

    aprobar_resp = client.post(f"/empresas/{cuil}/aprobar", headers=auth_headers(token))
    assert aprobar_resp.status_code == 200

    empresa = session.query(models.Empresa).filter_by(cuil=cuil).first()
    assert empresa.estado is True
    assert empresa.estado_solicitud == "aprobada"


@requires_real_db
def test_solicitud_rechazar_mantiene_empresa_inactiva(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    cuil = fake_cuil()
    client.post(
        "/register",
        json={
            "cuil": cuil,
            "nombre": "Empresa Rechazo Test",
            "rubro": "Testing",
            "cant_empleados": 2,
            "horario_trabajo": "9 a 18",
            "usuario_nombre": f"rej_user_{cuil}",
            "email": f"rej_{cuil}@example.com",
            "password": "ClaveSegura1",
        },
    )

    rechazar_resp = client.post(f"/empresas/{cuil}/rechazar", headers=auth_headers(token))
    assert rechazar_resp.status_code == 200

    empresa = session.query(models.Empresa).filter_by(cuil=cuil).first()
    assert empresa.estado_solicitud == "rechazada"
    assert empresa.estado is False


# ───────────────────────── /usuarios ─────────────────────────

@requires_real_db
def test_create_user_publico_in_polo_succeeds(real_client):
    client, session, token, polo_empresa = _admin_polo_client(real_client)
    rol_publico = get_or_create_role(session, "publico")
    suffix = fake_cuil()

    response = client.post(
        "/usuarios",
        json={
            "nombre": f"nuevo_publico_{suffix}",
            "email": f"nuevo_publico_{suffix}@example.com",
            "cuil": polo_empresa.cuil,
            "estado": True,
            "id_rol": rol_publico.id_rol,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["nombre"] == f"nuevo_publico_{suffix}"


@requires_real_db
def test_create_user_publico_outside_polo_rejected(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    empresa = create_empresa(session)
    rol_publico = get_or_create_role(session, "publico")
    suffix = fake_cuil()

    response = client.post(
        "/usuarios",
        json={
            "nombre": f"publico_malo_{suffix}",
            "email": f"publico_malo_{suffix}@example.com",
            "cuil": empresa.cuil,
            "estado": True,
            "id_rol": rol_publico.id_rol,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 400


@requires_real_db
def test_create_user_admin_empresa_via_admin_polo_rejected(real_client):
    """admin_empresa ya no se crea a mano, solo por /register + aprobacion."""
    client, session, token, _polo = _admin_polo_client(real_client)
    empresa = create_empresa(session)
    rol_admin_empresa = get_or_create_role(session, "admin_empresa")
    suffix = fake_cuil()

    response = client.post(
        "/usuarios",
        json={
            "nombre": f"admin_emp_{suffix}",
            "email": f"admin_emp_{suffix}@example.com",
            "cuil": empresa.cuil,
            "estado": True,
            "id_rol": rol_admin_empresa.id_rol,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 400


@requires_real_db
def test_update_and_disable_user(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    empresa = create_empresa(session)
    target_user, _password = create_user(session, empresa=empresa, rol_tipo="admin_empresa")

    update_resp = client.put(
        f"/usuarios/{target_user.id_usuario}",
        json={"estado": False},
        headers=auth_headers(token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["estado"] is False

    delete_resp = client.delete(f"/usuarios/{target_user.id_usuario}", headers=auth_headers(token))
    assert delete_resp.status_code == 204

    session.refresh(target_user)
    assert target_user.estado is False



# ───────────────────────── servicios del Polo + lotes ─────────────────────────

@requires_real_db
def test_serviciopolo_and_lote_crud(real_client):
    client, session, token, polo_empresa = _admin_polo_client(real_client)

    tipo = session.query(models.TipoServicioPolo).first()
    assert tipo is not None, "Debe existir al menos un tipo_servicio_polo sembrado"

    create_resp = client.post(
        "/serviciopolo",
        json={
            "nombre": "Servicio Test Integracion",
            "horario": "24hs",
            "datos": {},
            "propietario": "Polo 52",
            "id_tipo_servicio_polo": tipo.id_tipo_servicio_polo,
            "cuil": polo_empresa.cuil,
        },
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    servicio_id = create_resp.json()["id_servicio_polo"]

    lote_resp = client.post(
        "/lotes",
        json={"dueno": "Dueño Test", "lote": 999, "manzana": 999, "id_servicio_polo": servicio_id},
        headers=auth_headers(token),
    )
    assert lote_resp.status_code == 200, lote_resp.text
    lote_id = lote_resp.json()["id_lotes"]

    update_lote_resp = client.put(
        f"/lotes/{lote_id}",
        json={"latitud": -31.4, "longitud": -64.2},
        headers=auth_headers(token),
    )
    assert update_lote_resp.status_code == 200
    assert update_lote_resp.json()["latitud"] == -31.4

    delete_lote_resp = client.delete(f"/lotes/{lote_id}", headers=auth_headers(token))
    assert delete_lote_resp.status_code == 204

    delete_servicio_resp = client.delete(f"/serviciopolo/{servicio_id}", headers=auth_headers(token))
    assert delete_servicio_resp.status_code == 204


@requires_real_db
def test_list_empresas_usuarios_servicios_lotes_roles(real_client):
    client, session, token, _polo = _admin_polo_client(real_client)
    for path in ("/empresas", "/usuarios", "/serviciopolo", "/lotes", "/roles"):
        response = client.get(path, headers=auth_headers(token))
        assert response.status_code == 200, f"{path} -> {response.status_code}: {response.text}"
        assert isinstance(response.json(), list)
