# backend/tests/test_openapi_health.py
from tests.helpers import first_existing_path, ensure

def test_openapi_served(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200

def test_health_or_ping(client):
    path, _ = first_existing_path(
        client, "get",
        ["/health", "/status", "/ping", "/api/health", "/_health"]
    )
    ensure(path, "No hay health endpoint reconocido en OpenAPI")
    r = client.get(path)
    assert r.status_code in (200, 204)
