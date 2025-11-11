from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app import services
from app.config import SECRET_KEY, ALGORITHM


def setup_module():
    services.USED_RESET_TOKENS.clear()


def teardown_module():
    services.USED_RESET_TOKENS.clear()


def test_create_password_reset_token_embeds_email_and_type():
    token = services.create_password_reset_token("user@example.com", expires_minutes=5)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "password_reset"
    issued_at = datetime.fromtimestamp(payload["iat"])
    expires_at = datetime.fromtimestamp(payload["exp"])
    assert expires_at - issued_at == timedelta(minutes=5)
    assert payload["jti"] not in services.USED_RESET_TOKENS


def test_verify_password_reset_token_rejects_expired_token():
    expired_payload = {
        "sub": "user@example.com",
        "type": "password_reset",
        "jti": "test",
        "exp": datetime.utcnow() - timedelta(minutes=1),
    }
    token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        services.verify_password_reset_token(token)
    assert exc.value.status_code == 400
    assert exc.value.headers["X-Error-Type"] == "expired"


def test_consume_password_reset_token_marks_token_as_used():
    services.USED_RESET_TOKENS.clear()
    token = services.create_password_reset_token("user@example.com", expires_minutes=5)
    email = services.consume_password_reset_token(token)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert email == "user@example.com"
    assert services.is_token_already_used(payload["jti"]) is True
    with pytest.raises(HTTPException) as exc:
        services.consume_password_reset_token(token)
    assert exc.value.status_code == 400
    assert exc.value.headers["X-Error-Type"] == "used"


def test_compose_fallback_response_builds_human_readable_list():
    rows = [
        {
            "nombre_empresa": "Logistica Express",
            "descripcion": "Distribución regional",
            "telefono": "123",
            "id": 10,
        },
        {
            "nombre": "Coworking Polo",
            "datos": {"puestos": 12, "responsable": "Maria"},
        },
    ]
    text = services.compose_fallback_response(rows)
    assert "Logistica Express" in text
    assert "Coworking Polo" in text
    assert "id" not in text.lower()
    assert text.count("-") >= 2


def test_sanitize_response_text_removes_asterisks_and_bullets():
    dirty_text = "***\n• Nombre: Empresa\n  • Item"
    cleaned = services.sanitize_response_text(dirty_text)
    assert "*" not in cleaned
    assert "•" not in cleaned
    assert cleaned.startswith("- Nombre")
