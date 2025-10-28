from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_transcribe_requires_file_content(client: TestClient):
    response = client.post(
        "/api/voice/transcribe",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "El archivo de audio está vacío"


def test_transcribe_returns_text(client: TestClient):
    with patch("app.routes.voice.services.transcribe_audio", return_value="hola mundo"):
        response = client.post(
            "/api/voice/transcribe",
            files={"audio": ("audio.wav", b"123", "audio/wav")},
            data={"language": "es-ES"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["transcript"] == "hola mundo"


def test_synthesize_validates_empty_text(client: TestClient):
    response = client.post("/api/voice/synthesize", json={"text": ""})
    assert response.status_code == 400
    assert response.json()["detail"] == "El texto no puede estar vacío"


def test_synthesize_returns_audio_stream(client: TestClient):
    fake_audio = b"12345"
    with patch("app.routes.voice.services.text_to_speech", return_value=fake_audio):
        response = client.post("/api/voice/synthesize", json={"text": "Hola"})
    assert response.status_code == 200
    assert response.content == fake_audio
    assert response.headers["content-type"] == "audio/mpeg"


def test_voice_chat_requires_audio_or_text(client: TestClient):
    response = client.post("/api/voice/chat", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Debes enviar audio o texto"


def test_voice_chat_with_text_payload(client: TestClient):
    fake_result = {
        "text": "Respuesta",
        "audio_base64": "ZmFrZQ==",
        "db_results": [],
        "transcript": "Pregunta",
        "corrected_entity": None,
        "error": False,
    }
    with patch("app.routes.voice.services.get_chat_response_with_audio", return_value=fake_result):
        response = client.post("/api/voice/chat", json={"text": "Hola"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["text"] == "Respuesta"
    assert payload["data"]["audio_base64"] == "ZmFrZQ=="


def test_voice_test_endpoint_success(client: TestClient):
    fake_results = {"text_to_speech": {"status": " OK"}, "chat_response": {"status": " OK"}, "errors": [], "summary": " Todos los tests pasaron"}
    with patch("app.routes.voice.services.test_voice_pipeline", return_value=fake_results):
        response = client.get("/api/voice/test")
    assert response.status_code == 200
    assert response.json()["data"] == fake_results


def test_synthesize_base64_returns_payload(client: TestClient):
    fake_audio = b"bytes"
    with patch("app.routes.voice.services.text_to_speech", return_value=fake_audio):
        response = client.post("/api/voice/synthesize-base64", json={"text": "Hola"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["audio_base64"] == "Ynl0ZXM="
