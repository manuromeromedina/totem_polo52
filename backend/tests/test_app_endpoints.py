from unittest.mock import patch

from fastapi.testclient import TestClient


def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Bienvenido al API Polo52"
    assert "features" in payload


def test_health_endpoint_reports_voice_provider(client: TestClient):
    with patch("app.services.get_voice_services_status", return_value={"provider": "google"}):
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["services"]["voice_provider"] == "google"


def test_voice_status_endpoint(client: TestClient):
    fake_status = {"provider": "google", "services": {"google_cloud": {"speech_to_text": " Disponible"}}}
    with patch("app.routes.voice.services.get_voice_services_status", return_value=fake_status):
        response = client.get("/api/voice/status")
    assert response.status_code == 200
    assert response.json()["data"] == fake_status
