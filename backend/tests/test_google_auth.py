import pytest

GOOGLE_LOGIN = "/auth/google/login"

def test_google_oauth_login(client, monkeypatch):
    try:
        from app import google_auth
    except Exception:
        pytest.skip("No existe módulo app.google_auth para monkeypatch")

    def fake_verify_token(token):
        return {"email": "guser@example.com", "name": "GUser"}

    monkeypatch.setattr("app.google_auth", "verify_token", fake_verify_token)

    r = client.post(GOOGLE_LOGIN, json={"id_token": "FAKE"})
    assert r.status_code in (200, 201), r.text
    assert r.json().get("email") == "guser@example.com"
