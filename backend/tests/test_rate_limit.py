"""
Tests del rate limiter en memoria (app/rate_limit.py) y de los headers de
seguridad (app/security_headers.py).
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import _client_key, rate_limit, reset_rate_limits


def _fake_request(ip: str = "1.2.3.4", headers: dict = None) -> SimpleNamespace:
    headers = headers or {}
    return SimpleNamespace(
        headers=SimpleNamespace(get=lambda key, default=None: headers.get(key, default)),
        client=SimpleNamespace(host=ip),
    )


@pytest.fixture(autouse=True)
def _reset():
    reset_rate_limits()
    yield
    reset_rate_limits()


def test_client_key_prefers_x_forwarded_for():
    req = _fake_request(ip="10.0.0.1", headers={"x-forwarded-for": "203.0.113.5, 10.0.0.1"})
    assert _client_key(req) == "203.0.113.5"


def test_client_key_falls_back_to_cf_connecting_ip():
    req = _fake_request(ip="10.0.0.1", headers={"cf-connecting-ip": "198.51.100.9"})
    assert _client_key(req) == "198.51.100.9"


def test_client_key_falls_back_to_request_client_host():
    req = _fake_request(ip="192.168.1.50")
    assert _client_key(req) == "192.168.1.50"


def test_rate_limit_allows_up_to_the_configured_max():
    dependency = rate_limit("test-endpoint", max_requests=3, window_seconds=60)
    req = _fake_request()
    for _ in range(3):
        dependency(req)  # no debería lanzar


def test_rate_limit_blocks_after_max_requests():
    dependency = rate_limit("test-endpoint-2", max_requests=3, window_seconds=60)
    req = _fake_request()
    for _ in range(3):
        dependency(req)

    with pytest.raises(HTTPException) as exc:
        dependency(req)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_rate_limit_is_isolated_per_client_ip():
    dependency = rate_limit("test-endpoint-3", max_requests=1, window_seconds=60)
    dependency(_fake_request(ip="1.1.1.1"))

    with pytest.raises(HTTPException):
        dependency(_fake_request(ip="1.1.1.1"))

    # Otra IP tiene su propio balde: no debería verse afectada.
    dependency(_fake_request(ip="2.2.2.2"))


def test_rate_limit_is_isolated_per_bucket_name():
    dep_a = rate_limit("bucket-a", max_requests=1, window_seconds=60)
    dep_b = rate_limit("bucket-b", max_requests=1, window_seconds=60)
    req = _fake_request()

    dep_a(req)
    dep_b(req)  # bucket distinto: no debería estar afectado por dep_a

    with pytest.raises(HTTPException):
        dep_a(req)


def test_chat_endpoint_gets_rate_limited(client: TestClient):
    with patch("app.routes.chat.get_chat_response", return_value=("hola", [], None)):
        for _ in range(30):
            client.post("/chat/", json={"message": "hola"})

        response = client.post("/chat/", json={"message": "hola"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_security_headers_present_on_responses(client: TestClient):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Strict-Transport-Security" in response.headers
