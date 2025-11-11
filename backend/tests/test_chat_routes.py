from unittest.mock import patch

from fastapi.testclient import TestClient


def test_chat_endpoint_returns_reply(client: TestClient):
    fake_response = ("Hola", [{"empresa": "Logistica"}], "Logistica")
    with patch("app.routes.chat.get_chat_response", return_value=fake_response):
        response = client.post("/chat/", json={"message": "hola"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Hola"
    assert body["data"] == [{"empresa": "Logistica"}]
    assert body["corrected_entity"] == "Logistica"


def test_chat_endpoint_handles_errors(client: TestClient):
    with patch("app.routes.chat.get_chat_response", side_effect=RuntimeError("boom")):
        response = client.post("/chat/", json={"message": "hola"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Ha ocurrido un error interno. Por favor, inténtalo nuevamente más tarde."
