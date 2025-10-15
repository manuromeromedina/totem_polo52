# backend/tests/test_admin_cache.py
import pytest
from tests.helpers import auth_headers
from tests.test_auth_flow import _signup, _login

EMPRESAS = "/empresas"
ALL = "/all"
ROLES = "/roles"
CACHE_STATUS = "/password-reset/cache-status"
CLEANUP = "/password-reset/cleanup-cache"

def _extract_cuil_from_empresas_payload(payload):
    if not isinstance(payload, list):
        return None
    for item in payload:
        for key in ("cuil", "CUIL", "cuit", "CUIT"):
            v = item.get(key)
            if v not in (None, "", 0):
                return v
    return None

def _get_any_existing_cuil_public(client):
    """
    Intenta obtener CUIL sin autenticación:
    1) GET /empresas (si es público)
    2) GET /all y buscar campo empresas[*].cuil
    Devuelve un CUIL o None.
    """
    # 1) Intento directo /empresas
    r = client.get(EMPRESAS)
    if r.status_code == 200:
        cuil = _extract_cuil_from_empresas_payload(r.json())
        if cuil:
            return cuil

    # 2) Intento /all (si existe y es público)
    r2 = client.get(ALL)
    if r2.status_code == 200:
        data = r2.json()
        # soporta varias formas: {"empresas":[...]} o {"data":{"empresas":[...]}}
        empresas = None
        if isinstance(data, dict):
            if isinstance(data.get("empresas"), list):
                empresas = data["empresas"]
            elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("empresas"), list):
                empresas = data["data"]["empresas"]
        if empresas:
            cuil = _extract_cuil_from_empresas_payload(empresas)
            if cuil:
                return cuil

    return None

def _find_admin_role_id(client):
    r = client.get(ROLES)
    if r.status_code != 200:
        return 1
    roles = r.json()
    if not isinstance(roles, list) or not roles:
        return 1

    def is_admin_like(role):
        for key in ("nombre", "name", "rol", "role", "descripcion", "description"):
            v = role.get(key)
            if isinstance(v, str) and "admin" in v.lower():
                return True
        return False

    for role in roles:
        if is_admin_like(role):
            for id_key in ("id", "id_rol", "role_id"):
                if id_key in role:
                    return role[id_key]
    for role in roles:
        for id_key in ("id", "id_rol", "role_id"):
            if id_key in role:
                return role[id_key]
    return 1

def _ensure_admin_token(client, email, pwd):
    cuil = _get_any_existing_cuil_public(client)
    if not cuil:
        pytest.skip("No pude obtener un CUIL público desde /empresas ni /all; no puedo registrar admin sin romper FK.")
    admin_role_id = _find_admin_role_id(client)
    try:
        _signup(client, email, pwd, nombre="Admin", cuil=cuil, id_rol=admin_role_id)
    except AssertionError:
        # si ya existe el usuario, seguimos
        pass
    return _login(client, email, pwd)

def test_admin_cache_status_and_cleanup(client, monkeypatch):
    # mocks de servicios
    try:
        import app.services as services  # noqa: F401
    except Exception:
        pytest.skip("No existe app.services para monkeypatch")

    state = {"count": 5, "cleaned": False}

    def fake_get_used_tokens_count():
        return state["count"]

    def fake_cleanup_used_tokens():
        state["cleaned"] = True
        state["count"] = 0

    monkeypatch.setattr("app.services.get_used_tokens_count", fake_get_used_tokens_count)
    monkeypatch.setattr("app.services.cleanup_used_tokens", fake_cleanup_used_tokens)

    # crear admin real usando CUIL obtenido sin auth (si no, skip)
    token = _ensure_admin_token(client, "admin@x.com", "Admin!234")

    # GET cache status
    r = client.get(CACHE_STATUS, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert r.json().get("used_tokens_count") == 5

    # POST cleanup
    r = client.post(CLEANUP, headers=auth_headers(token))
    assert r.status_code in (200, 204), r.text
    if r.status_code == 200:
        body = r.json()
        tr = body.get("tokens_removed")
        if tr is not None:
            assert tr in (5, 0)
    assert state["cleaned"] is True
