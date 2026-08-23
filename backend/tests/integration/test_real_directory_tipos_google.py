"""
Tests de integracion reales (contra Supabase, con rollback) para el
directorio publico, los catalogos de /tipos y el arranque del login con
Google.

Nota sobre Google OAuth: /auth/google/callback y /register-pending
requieren un `code` de intercambio real emitido por Google -- no se puede
probar "de verdad" sin credenciales reales de un usuario de Google, así que
acá solo se verifica que /auth/google/login arma correctamente el redirect
a Google (la parte que sí depende 100% de nuestro código).
"""
import pytest

from tests.integration.conftest import (
    requires_real_db,
    create_empresa,
    create_user,
    login,
    auth_headers,
)


# ───────────────────────── directorio ─────────────────────────

@requires_real_db
def test_directorio_requires_authentication(real_client):
    client, _session = real_client
    response = client.get("/empresas/directorio")
    assert response.status_code == 401


@requires_real_db
def test_directorio_accessible_by_any_logged_in_role(real_client):
    client, session = real_client
    empresa = create_empresa(session, estado=True)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.get("/empresas/directorio", headers=auth_headers(token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # La empresa recien creada (activa) tiene que aparecer en el directorio.
    assert any(e["nombre"] == empresa.nombre for e in response.json())


@requires_real_db
def test_search_by_name(real_client):
    client, session = real_client
    empresa = create_empresa(session, nombre="Buscable Unica Test SRL")
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.get("/search", params={"name": "Buscable Unica Test"}, headers=auth_headers(token))
    assert response.status_code == 200
    assert any(e["nombre"] == empresa.nombre for e in response.json())


@requires_real_db
def test_search_returns_404_when_nothing_matches(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.get(
        "/search", params={"name": "Empresa Que Definitivamente No Existe XYZ123"}, headers=auth_headers(token)
    )
    assert response.status_code == 404


# ───────────────────────── catalogos publicos /tipos ─────────────────────────

@requires_real_db
def test_tipos_catalogs_are_fully_public(real_client):
    client, _session = real_client
    for path in ("/tipos/vehiculo", "/tipos/servicio", "/tipos/contacto", "/tipos/servicio-polo"):
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
        assert isinstance(response.json(), list)


# ───────────────────────── Google OAuth ─────────────────────────

@requires_real_db
def test_google_login_redirects_to_google(real_client):
    client, _session = real_client
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "accounts.google.com" in response.headers["location"]
