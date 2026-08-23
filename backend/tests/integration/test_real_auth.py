"""
Tests de integracion reales (contra Supabase, con rollback) para el modulo
de autenticacion: registro, login, logout, cambio de contraseña logueado y
recuperacion de contraseña por email.
"""
import pytest

from app import services
from app.routes import auth as auth_routes
from tests.integration.conftest import (
    requires_real_db,
    fake_cuil,
    create_empresa,
    create_user,
    login,
    auth_headers,
)


@pytest.fixture(autouse=True)
def mute_emails_and_attempts(monkeypatch):
    """No mandar emails reales durante los tests y limpiar el estado en
    memoria de intentos fallidos de cambio de contraseña entre tests."""
    for fn_name in (
        "send_registration_received_email",
        "send_password_change_notification",
        "send_password_change_failure_notification",
        "send_password_reset_email",
    ):
        monkeypatch.setattr(auth_routes.services, fn_name, lambda *a, **k: True)
    auth_routes._change_pw_attempts.clear()
    yield
    auth_routes._change_pw_attempts.clear()


# ───────────────────────── /register ─────────────────────────

@requires_real_db
def test_register_creates_pending_company_and_user(real_client):
    client, session = real_client
    cuil = fake_cuil()
    response = client.post(
        "/register",
        json={
            "cuil": cuil,
            "nombre": "Empresa Registro Test",
            "rubro": "Testing",
            "cant_empleados": 3,
            "horario_trabajo": "9 a 18",
            "usuario_nombre": f"reg_user_{cuil}",
            "email": f"reg_{cuil}@example.com",
            "password": "ClaveSegura1",
        },
    )
    assert response.status_code == 200, response.text

    from app import models

    empresa = session.query(models.Empresa).filter_by(cuil=cuil).first()
    assert empresa is not None
    assert empresa.estado is False
    assert empresa.estado_solicitud == "pendiente"

    usuario = session.query(models.Usuario).filter_by(cuil=cuil).first()
    assert usuario is not None
    assert any(r.tipo_rol == "admin_empresa" for r in usuario.roles)


@requires_real_db
def test_register_rejects_duplicate_cuil(real_client):
    client, session = real_client
    empresa = create_empresa(session)

    response = client.post(
        "/register",
        json={
            "cuil": empresa.cuil,
            "nombre": "Otra empresa",
            "rubro": "Testing",
            "cant_empleados": 3,
            "horario_trabajo": "9 a 18",
            "usuario_nombre": f"dup_user_{fake_cuil()}",
            "email": f"dup_{fake_cuil()}@example.com",
            "password": "ClaveSegura1",
        },
    )
    assert response.status_code == 400
    assert "cuil" in response.json()["detail"].lower()


# ───────────────────────── /login ─────────────────────────

@requires_real_db
def test_login_succeeds_with_correct_credentials(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")

    response = client.post("/login", data={"username": user.nombre, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["tipo_rol"] == "publico"
    assert body["access_token"]


@requires_real_db
def test_login_fails_with_wrong_password(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, _ = create_user(session, empresa=empresa, rol_tipo="publico")

    response = client.post("/login", data={"username": user.nombre, "password": "ClaveIncorrecta1"})
    assert response.status_code == 401


@requires_real_db
def test_login_fails_for_disabled_user(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico", estado=False)

    response = client.post("/login", data={"username": user.nombre, "password": password})
    assert response.status_code == 403


@requires_real_db
def test_login_fails_for_inactive_empresa(real_client):
    client, session = real_client
    empresa = create_empresa(session, estado=False)
    user, password = create_user(session, empresa=empresa, rol_tipo="admin_empresa")

    response = client.post("/login", data={"username": user.nombre, "password": password})
    assert response.status_code == 403


@requires_real_db
def test_login_fails_for_unknown_user(real_client):
    client, _session = real_client
    response = client.post("/login", data={"username": "usuario_que_no_existe_xyz", "password": "loquesea1A"})
    assert response.status_code == 401


# ───────────────────────── /logout ─────────────────────────

@requires_real_db
def test_logout_succeeds_with_valid_token(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.post("/logout", headers=auth_headers(token))
    assert response.status_code == 200


@requires_real_db
def test_logout_rejects_invalid_token(real_client):
    client, _session = real_client
    response = client.post("/logout", headers=auth_headers("no-soy-un-jwt-real"))
    assert response.status_code == 401


# ───────────────────────── /change-password-direct ─────────────────────────

@requires_real_db
def test_change_password_direct_success(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.post(
        "/change-password-direct",
        json={"current_password": password, "new_password": "NuevaClaveSegura1", "confirm_password": "NuevaClaveSegura1"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Confirmar que la nueva contraseña realmente quedo activa: relogin.
    relogin = client.post(
        "/login", data={"username": user.nombre, "password": "NuevaClaveSegura1"}
    )
    assert relogin.status_code == 200


@requires_real_db
def test_change_password_direct_rejects_wrong_current_password(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.post(
        "/change-password-direct",
        json={"current_password": "ClaveMalaXX1", "new_password": "NuevaClaveSegura1", "confirm_password": "NuevaClaveSegura1"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200  # la ruta devuelve 200 con success=False
    body = response.json()
    assert body["success"] is False
    assert body["wrong_current"] is True


@requires_real_db
def test_change_password_direct_rejects_mismatched_confirmation(real_client):
    """
    El propio schema Pydantic (ChangePasswordDirect.passwords_match) ya
    rechaza el mismatch con 422 antes de llegar a la ruta -- el chequeo
    manual `dto.new_password != dto.confirm_password` dentro de la ruta es
    inalcanzable (ver nota de optimizacion sobre codigo muerto).
    """
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.post(
        "/change-password-direct",
        json={"current_password": password, "new_password": "NuevaClaveSegura1", "confirm_password": "OtraClaveDistinta1"},
        headers=auth_headers(token),
    )
    assert response.status_code == 422
    assert "no coinciden" in response.text.lower()


# ───────────────────────── recuperacion de contraseña ─────────────────────────

@requires_real_db
def test_forgot_password_flow_end_to_end(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, _old_password = create_user(session, empresa=empresa, rol_tipo="publico")

    forgot_response = client.post("/forgot-password", json={"email": user.email})
    assert forgot_response.status_code == 200

    token = services.create_password_reset_token(user.email, expires_minutes=60)

    verify_response = client.post("/password-reset/verify-token", params={"token": token})
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True

    confirm_response = client.post(
        "/forgot-password/confirm",
        json={"token": token, "new_password": "OtraClaveNueva1", "confirm_password": "OtraClaveNueva1"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["success"] is True

    relogin = client.post("/login", data={"username": user.nombre, "password": "OtraClaveNueva1"})
    assert relogin.status_code == 200


@requires_real_db
def test_forgot_password_rejects_unknown_email(real_client):
    client, _session = real_client
    response = client.post("/forgot-password", json={"email": "no-existe-esta-cuenta@example.com"})
    assert response.status_code == 404


@requires_real_db
def test_forgot_password_rejects_disabled_account(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, _password = create_user(session, empresa=empresa, rol_tipo="publico", estado=False)

    response = client.post("/forgot-password", json={"email": user.email})
    assert response.status_code == 403


# ───────────────────────── /bienvenida-vista ─────────────────────────

@requires_real_db
def test_bienvenida_vista_marks_flag_false(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)

    response = client.post("/bienvenida-vista", headers=auth_headers(token))
    assert response.status_code == 200

    session.refresh(user)
    assert user.mostrar_bienvenida is False
