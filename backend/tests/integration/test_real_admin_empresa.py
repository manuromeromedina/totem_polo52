"""
Tests de integracion reales (contra Supabase, con rollback) para las rutas
de admin_empresa: perfil de empresa, vehiculos, servicios, contactos e
informacion comercial (wizard + edicion directa).
"""
import pytest

from tests.integration.conftest import (
    requires_real_db,
    create_empresa,
    create_user,
    login,
    auth_headers,
)


def _admin_empresa_client(real_client):
    client, session = real_client
    empresa = create_empresa(session, nombre="Empresa Admin Test")
    user, password = create_user(session, empresa=empresa, rol_tipo="admin_empresa")
    token = login(client, user.nombre, password)
    return client, session, token, empresa


# ───────────────────────── /me y /companies/me ─────────────────────────

@requires_real_db
def test_read_me_returns_full_company_detail(real_client):
    client, session, token, empresa = _admin_empresa_client(real_client)
    response = client.get("/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["cuil"] == empresa.cuil


@requires_real_db
def test_update_my_company(real_client):
    client, session, token, empresa = _admin_empresa_client(real_client)
    response = client.put(
        "/companies/me",
        json={"cant_empleados": 12, "observaciones": "actualizado por test", "horario_trabajo": "8 a 17"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["horario_trabajo"] == "8 a 17"


@requires_real_db
def test_empresa_routes_reject_admin_polo_user(real_client):
    """require_empresa_role tiene que rechazar a un admin_polo."""
    from app.routes import admin_users as admin_routes

    client, session = real_client
    polo_empresa_cuil = admin_routes.POLO_CUIL
    from app import models

    polo_empresa = session.query(models.Empresa).filter_by(cuil=polo_empresa_cuil).first()
    user, password = create_user(session, empresa=polo_empresa, rol_tipo="admin_polo")
    token = login(client, user.nombre, password)

    response = client.get("/me", headers=auth_headers(token))
    assert response.status_code == 403


# ───────────────────────── vehiculos ─────────────────────────

@requires_real_db
def test_vehiculo_crud_flow(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)

    create_resp = client.post(
        "/vehiculos",
        json={
            "id_tipo_vehiculo": 1,
            "horarios": "8 a 18",
            "frecuencia": "diaria",
            "datos": {"cantidad": 2, "patente": "AB123CD", "carga": "mediana"},
        },
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    veh_id = create_resp.json()["id_vehiculo"]

    update_resp = client.put(
        f"/vehiculos/{veh_id}",
        json={
            "id_tipo_vehiculo": 1,
            "horarios": "9 a 19",
            "frecuencia": "semanal",
            "datos": {"cantidad": 3, "patente": "AB123CD", "carga": "alta"},
        },
        headers=auth_headers(token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["horarios"] == "9 a 19"

    delete_resp = client.delete(f"/vehiculos/{veh_id}", headers=auth_headers(token))
    assert delete_resp.status_code == 204


@requires_real_db
def test_vehiculo_corporativo_requires_carga_field(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    response = client.post(
        "/vehiculos",
        json={
            "id_tipo_vehiculo": 1,
            "horarios": "8 a 18",
            "frecuencia": "diaria",
            "datos": {"cantidad": 2, "patente": "AB123CD"},  # falta 'carga'
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 400


@requires_real_db
def test_vehiculo_update_rejects_id_not_owned_by_company(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    response = client.put(
        "/vehiculos/999999999",
        json={"id_tipo_vehiculo": 1, "horarios": "8 a 18", "frecuencia": "diaria", "datos": {}},
        headers=auth_headers(token),
    )
    assert response.status_code == 404


# ───────────────────────── servicios ─────────────────────────

@requires_real_db
def test_servicio_crud_flow(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    from app import models

    tipo_servicio = session.query(models.TipoServicio).first()
    assert tipo_servicio is not None

    create_resp = client.post(
        "/servicios",
        json={"datos": {"detalle": "servicio de test"}, "id_tipo_servicio": tipo_servicio.id_tipo_servicio},
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    servicio_id = create_resp.json()["id_servicio"]

    update_resp = client.put(
        f"/servicios/{servicio_id}",
        json={"datos": {"detalle": "servicio editado"}},
        headers=auth_headers(token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["datos"]["detalle"] == "servicio editado"

    delete_resp = client.delete(f"/servicios/{servicio_id}", headers=auth_headers(token))
    assert delete_resp.status_code == 204


# ───────────────────────── contactos ─────────────────────────

@requires_real_db
def test_contacto_crud_flow(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    from app import models

    tipo_contacto = session.query(models.TipoContacto).first()
    assert tipo_contacto is not None

    create_resp = client.post(
        "/contactos",
        json={
            "id_tipo_contacto": tipo_contacto.id_tipo_contacto,
            "nombre": "Contacto Test",
            "telefono": "3511234567",
            "datos": {"correo": "contacto@test.com"},
            "direccion": "Calle Falsa 123",
        },
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 200, create_resp.text
    contacto_id = create_resp.json()["id_contacto"]

    update_resp = client.put(
        f"/contactos/{contacto_id}",
        json={
            "id_tipo_contacto": tipo_contacto.id_tipo_contacto,
            "nombre": "Contacto Editado",
            "telefono": "3511234567",
            "datos": {"correo": "contacto@test.com"},
            "direccion": "Calle Falsa 123",
        },
        headers=auth_headers(token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["nombre"] == "Contacto Editado"

    delete_resp = client.delete(f"/contactos/{contacto_id}", headers=auth_headers(token))
    assert delete_resp.status_code == 204


# ───────────────────────── catalogos (tipos/*) ─────────────────────────

@requires_real_db
def test_company_scoped_tipos_catalogs(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    for path in ("/tipos/vehiculo", "/tipos/servicio", "/tipos/contacto"):
        response = client.get(path, headers=auth_headers(token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ───────────────────────── informacion comercial ─────────────────────────

@requires_real_db
def test_comercial_info_404_before_wizard(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    response = client.get("/companies/me/comercial", headers=auth_headers(token))
    assert response.status_code == 404


@requires_real_db
def test_comercial_wizard_completes_all_questions(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    answers = [
        "Vendemos repuestos industriales",
        "B2B",
        "si",
        "9 a 18",
        "Medio",
        "Ambas",
        "no aplica",
        "no tenemos",
        "Todo en orden",
    ]

    # Primer POST sin message: debe devolver la primera pregunta sin avanzar.
    first = client.post("/companies/me/comercial/chat", json={"message": None}, headers=auth_headers(token))
    assert first.status_code == 200
    assert first.json()["done"] is False
    assert first.json()["progreso_actual"] == 0

    last_response = None
    for answer in answers:
        last_response = client.post(
            "/companies/me/comercial/chat", json={"message": answer}, headers=auth_headers(token)
        )
        assert last_response.status_code == 200, last_response.text

    assert last_response.json()["done"] is True

    info_response = client.get("/companies/me/comercial", headers=auth_headers(token))
    assert info_response.status_code == 200
    body = info_response.json()
    assert body["completado"] is True
    assert body["publico_objetivo"] == "B2B"
    assert body["atiende_publico"] is True
    assert body["rango_precios"] == "Medio"


@requires_real_db
def test_comercial_edit_after_wizard_completed(real_client):
    client, session, token, _empresa = _admin_empresa_client(real_client)
    answers = [
        "Vendemos repuestos industriales", "B2B", "si", "9 a 18",
        "Medio", "Ambas", "no aplica", "no tenemos", "Todo en orden",
    ]
    for answer in answers:
        client.post("/companies/me/comercial/chat", json={"message": answer}, headers=auth_headers(token))

    edit_resp = client.put(
        "/companies/me/comercial",
        json={"rango_precios": "Premium"},
        headers=auth_headers(token),
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["rango_precios"] == "Premium"
