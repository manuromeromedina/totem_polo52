from tests.test_auth_flow import _signup, _login
from tests.helpers import auth_headers

POLO_ME = "/polo/me"
POLO_CHANGE_REQ = "/polo/change-password-request"
COMPANIES_ME = "/companies/me"

def test_polo_me_and_companies_me(client):
    email, pwd = "manager@corp.com", "M4nager!234"
    _signup(client, email, pwd, nombre="Manager")
    token = _login(client, email, pwd)

    r = client.get(POLO_ME, headers=auth_headers(token))
    assert r.status_code in (200, 204)

    r = client.get(COMPANIES_ME, headers=auth_headers(token))
    assert r.status_code in (200, 204)

def test_polo_change_password_request(client):
    email, pwd = "polo@corp.com", "Pol0!234"
    _signup(client, email, pwd, nombre="PoloUser")
    token = _login(client, email, pwd)

    r = client.post(POLO_CHANGE_REQ, headers=auth_headers(token))
    assert r.status_code in (200, 204)
