"""
Tests de integracion reales (contra Supabase, con rollback) para
/api/voice/*. Se mockea unicamente la llamada externa a Gemini/Google Cloud
(services.get_chat_response_with_audio) -- todo lo demas (auth real,
persistencia real en chat_mensaje, lectura real del historial) corre
contra la base real.
"""
from unittest.mock import patch

import pytest

from tests.integration.conftest import (
    requires_real_db,
    create_empresa,
    create_user,
    login,
    auth_headers,
)


def _publico_client(real_client):
    client, session = real_client
    empresa = create_empresa(session)
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")
    token = login(client, user.nombre, password)
    return client, session, token, user


@requires_real_db
def test_voice_status_endpoint(real_client):
    client, _session, token, _user = _publico_client(real_client)
    response = client.get("/api/voice/status", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["success"] is True


@requires_real_db
def test_voice_chat_accepts_any_authenticated_role(real_client):
    """
    /api/voice/* esta gateado a nivel router por Depends(get_current_user),
    NO por require_public_role -- cualquier rol autenticado (admin_polo,
    admin_empresa o publico) puede usarlo hoy. Esto es una inconsistencia
    con el guard de rol 'publico' que usa el frontend en /chat (ver nota en
    FUNCIONALIDADES.md), pero no es una falla de autenticacion: sigue
    exigiendo un JWT valido, solo no restringe por rol especifico.
    """
    from app import models
    from app.routes import admin_users as admin_routes

    client, session, _token, _user = _publico_client(real_client)
    polo_empresa = session.query(models.Empresa).filter_by(cuil=admin_routes.POLO_CUIL).first()
    admin_user, admin_password = create_user(session, empresa=polo_empresa, rol_tipo="admin_polo")
    admin_token = login(client, admin_user.nombre, admin_password)

    fake_result = {
        "text": "hola", "audio_base64": "", "transcript": None,
        "db_results": [], "corrected_entity": None, "error": False,
    }
    with patch("app.routes.voice.services.get_chat_response_with_audio", return_value=fake_result):
        response = client.post(
            "/api/voice/chat", json={"text": "hola"}, headers=auth_headers(admin_token)
        )
    assert response.status_code == 200


@requires_real_db
def test_voice_chat_rejects_unauthenticated_request(real_client):
    client, _session = real_client
    response = client.post("/api/voice/chat", json={"text": "hola"})
    assert response.status_code == 401


@requires_real_db
def test_voice_chat_persists_turn_and_appears_in_history(real_client):
    client, session, token, user = _publico_client(real_client)

    fake_result = {
        "text": "Respuesta de prueba del bot",
        "audio_base64": "ZmFrZQ==",
        "transcript": None,
        "db_results": [],
        "corrected_entity": None,
        "error": False,
    }
    with patch("app.routes.voice.services.get_chat_response_with_audio", return_value=fake_result):
        response = client.post(
            "/api/voice/chat", json={"text": "Que empresas hay en el parque?"}, headers=auth_headers(token)
        )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["text"] == "Respuesta de prueba del bot"

    from app import models

    mensajes = (
        session.query(models.ChatMensaje)
        .filter_by(id_usuario=user.id_usuario)
        .order_by(models.ChatMensaje.id_mensaje)
        .all()
    )
    assert len(mensajes) == 2
    assert mensajes[0].remitente == "user"
    assert mensajes[0].contenido == "Que empresas hay en el parque?"
    assert mensajes[1].remitente == "bot"
    assert mensajes[1].contenido == "Respuesta de prueba del bot"

    history_response = client.get("/api/voice/history", headers=auth_headers(token))
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 2
    assert history[0]["remitente"] == "user"
    assert history[1]["remitente"] == "bot"


@requires_real_db
def test_voice_history_is_scoped_per_user(real_client):
    client, session, token_a, user_a = _publico_client(real_client)
    empresa_b = create_empresa(session)
    user_b, password_b = create_user(session, empresa=empresa_b, rol_tipo="publico")
    token_b = login(client, user_b.nombre, password_b)

    fake_result = {
        "text": "Respuesta A", "audio_base64": "", "transcript": None,
        "db_results": [], "corrected_entity": None, "error": False,
    }
    with patch("app.routes.voice.services.get_chat_response_with_audio", return_value=fake_result):
        client.post("/api/voice/chat", json={"text": "Pregunta de A"}, headers=auth_headers(token_a))

    history_b = client.get("/api/voice/history", headers=auth_headers(token_b))
    assert history_b.status_code == 200
    assert history_b.json() == []


@requires_real_db
def test_voice_chat_requires_audio_or_text(real_client):
    client, _session, token, _user = _publico_client(real_client)
    response = client.post("/api/voice/chat", json={}, headers=auth_headers(token))
    assert response.status_code == 400
