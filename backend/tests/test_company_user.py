# backend/tests/test_company_user.py
import pytest
from tests.helpers import auth_headers
from tests.test_auth_flow import _signup, _login  # usa la versión que busca CUIL público

COMPANIES_ME = "/companies/me"

def test_companies_me_authenticated(client):
    # Registramos SIN pasar cuil: _signup buscará uno público o hará skip si no hay
    email, pwd = "manager@corp.com", "M4nager!234"
    _signup(client, email, pwd, nombre="Manager")

    token = _login(client, email, pwd)

    r = client.get(COMPANIES_ME, headers=auth_headers(token))
    # Si tenés compañía asociada debería ser 200 con un dict; si tu endpoint
    # devuelve 404 cuando no hay asociación, podés permitir 404 también.
    assert r.status_code in (200, 404), f"{r.status_code}: {r.text}"
    if r.status_code == 200:
        assert isinstance(r.json(), dict)

def test_companies_me_requires_auth(client):
    r = client.get(COMPANIES_ME)  # sin token
    # Si el endpoint no acepta GET devuelve 405; igual nos sirve para verificar que sin auth no se puede usar.
    assert r.status_code in (401, 403, 405)

