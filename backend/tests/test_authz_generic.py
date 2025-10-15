from tests.helpers import first_existing_path

def test_protected_endpoints_without_token_are_rejected(client):
    # intenta con /me si existe
    me, _ = first_existing_path(client, "get", ["/me", "/users/me", "/auth/me"])
    if not me:
        return
    r = client.get(me)
    assert r.status_code in (401, 403)
