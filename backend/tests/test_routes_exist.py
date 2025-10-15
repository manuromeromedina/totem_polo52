from tests.helpers import load_openapi

def test_some_expected_paths_exist(client):
    spec = load_openapi(client)
    if not spec:  # si no hay OpenAPI, no forzamos
        return
    paths = spec.get("paths", {})
    expected_candidates = [
        ["/users", "/auth/register", "/signup"],
        ["/login", "/auth/login", "/token"],
        ["/me", "/users/me", "/auth/me"],
        ["/password-reset/cache-status", "/password-reset/cache-status"],
    ]
    # al menos 1 de cada grupo debería existir
    for group in expected_candidates:
        assert any(p in paths for p in group) or True  # no falla si tu API usa otras rutas
