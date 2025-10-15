from tests.test_auth_flow import _signup, _login
from tests.helpers import auth_headers

USUARIOS = "/usuarios"
USUARIOS_LIMITS = "/usuarios/limits-status"

def test_usuarios_list_and_limits(client):
    email, pwd = "adminlist@x.com", "Adm!2345"
    _signup(client, email, pwd)
    token = _login(client, email, pwd)

    r = client.get(USUARIOS, headers=auth_headers(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = client.get(USUARIOS_LIMITS, headers=auth_headers(token))
    assert r.status_code in (200, 204)
