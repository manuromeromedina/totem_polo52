# backend/tests/test_auth_flow.py
import pytest
from tests.helpers import auth_headers

# Rutas reales
SIGNUP_PATH = "/register"
LOGIN_PATH  = "/login"
ME_PATH     = "/me"
EMPRESAS    = "/empresas"
ALL         = "/all"

def _extract_cuil_from_list(items):
    if not isinstance(items, list):
        return None
    for it in items:
        for k in ("cuil", "CUIL", "cuit", "CUIT"):
            v = it.get(k)
            if v not in (None, "", 0):
                return v
    return None

def _get_public_cuil(client):
    # 1) /empresas sin auth
    r = client.get(EMPRESAS)
    if r.status_code == 200:
        cuil = _extract_cuil_from_list(r.json())
        if cuil:
            return cuil
    # 2) /all sin auth
    r = client.get(ALL)
    if r.status_code == 200 and isinstance(r.json(), dict):
        data = r.json()
        empresas = None
        if isinstance(data.get("empresas"), list):
            empresas = data["empresas"]
        elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("empresas"), list):
            empresas = data["data"]["empresas"]
        if empresas:
            cuil = _extract_cuil_from_list(empresas)
            if cuil:
                return cuil
    return None

def _signup(client, email, password, nombre="Test", cuil=None, id_rol=1):
    if cuil is None:
        cuil = _get_public_cuil(client)
        if not cuil:
            pytest.skip("No pude obtener CUIL público para registrar usuario (FK empresa.cuil).")
    payload = {
        "email": email,
        "password": password,
        "nombre": nombre,
        "cuil": cuil,
        "id_rol": id_rol,
    }
    r = client.post(SIGNUP_PATH, json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()

def _login(client, email, password):
    data = {"username": email, "password": password}
    r = client.post(LOGIN_PATH, data=data)
    assert r.status_code == 200, r.text
    token = r.json().get("access_token")
    assert token
    return token

def test_signup_login_me(client):
    email, pwd = "alice@example.com", "S3gura!2025"
    _signup(client, email, pwd)
    token = _login(client, email, pwd)

    r = client.get(ME_PATH, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert r.json().get("email") == email

def test_me_requires_auth(client):
    r = client.get(ME_PATH)  # sin token
    assert r.status_code in (401, 403)
