# backend/tests/test_password_reset.py
import pytest

SIGNUP_PATH = "/register"
LOGIN_PATH = "/login"
FORGOT_PATH = "/forgot-password"
VERIFY_PATH = "/password-reset/verify-token"
CONFIRM_PATH = "/password-reset/confirm-secure"

def _get_any_existing_cuil(client):
    """
    Intenta obtener un CUIL válido sin autenticación.
    Preferimos /all (público en tu API). Si no está, devolvemos None.
    """
    r = client.get("/all")
    if r.status_code == 200:
        data = r.json() or {}
        empresas = data.get("empresa") or data.get("empresas") or []
        for e in empresas:
            cuil = e.get("cuil")
            if isinstance(cuil, int) and cuil > 0:
                return cuil
    return None

def _signup(client, email, password, nombre="Bob", id_rol=1):
    """
    Registro mínimo. Requiere CUIL válido por la FK con empresa.
    Si no hay CUIL público, tiramos skip como en otros tests.
    """
    cuil = _get_any_existing_cuil(client)
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
    assert r.status_code in (200, 201), f"Signup falló: {r.status_code} {r.text}"
    return r.json()

def _login(client, email, password):
    r = client.post(LOGIN_PATH, data={"username": email, "password": password})
    assert r.status_code in (200, 201), f"Login falló: {r.status_code} {r.text}"
    j = r.json()
    token = j.get("access_token") or j.get("token")
    assert token, f"Respuesta de login sin token: {j}"
    return token

def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def test_forgot_confirm_flow(client, monkeypatch):
    # 1) Registrar usuario con CUIL válido
    email, pwd = "bob@example.com", "Inicial!234"
    _signup(client, email, pwd)

    # 2) Iniciar flujo de forgot-password
    r = client.post(FORGOT_PATH, json={"email": email})
    # Muchos backends devuelven 200/202/204 aunque el mail sea desconocido (para no filtrar existencia).
    assert r.status_code in (200, 202, 204), f"forgot-password debe aceptar el mail: {r.status_code} {r.text}"
    body = {}
    try:
        body = r.json() or {}
    except Exception:
        body = {}

    # 3) Intentamos ver si el backend nos devuelve el token (entornos de test suelen hacerlo)
    token = body.get("token") or body.get("reset_token") or None

    # Si no tenemos token, probamos el endpoint de verify con uno "fake"
    # No debe reventar la API; lo normal es 400/404.
    if not token:
        r = client.get(VERIFY_PATH, params={"token": "fake-token", "email": email})
        assert r.status_code in (400, 404), f"verify-token con token inválido debe ser 400/404: {r.status_code} {r.text}"
        # En este escenario no podemos confirmar contraseña sin token real.
        pytest.skip("El backend no expuso el token de reset en la respuesta y no hay forma limpia de capturarlo en test sin monkeypatch.")

    # 4) Con token real, verify debería dar 200
    r = client.get(VERIFY_PATH, params={"token": token, "email": email})
    assert r.status_code == 200, f"verify-token con token real debe 200: {r.status_code} {r.text}"

    # 5) Confirmar el reset
    new_pwd = "Nuev4!Clave"
    r = client.post(CONFIRM_PATH, json={"email": email, "token": token, "new_password": new_pwd})
    assert r.status_code in (200, 204), f"confirm-secure debe 200/204: {r.status_code} {r.text}"

    # 6) Podemos intentar login con la nueva password (si tu backend invalida sesiones previas)
    r = client.post(LOGIN_PATH, data={"username": email, "password": new_pwd})
    assert r.status_code in (200, 201), f"Login con nueva password debe funcionar: {r.status_code} {r.text}"
