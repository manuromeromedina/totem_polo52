# backend/tests/helpers.py
import re
import pytest

def load_openapi(client):
    r = client.get("/openapi.json")
    return r.json() if r.status_code == 200 else None

def first_existing_path(client, method, candidates):
    """
    Devuelve (path, params) si existe en el OpenAPI. Si no, (None, []).
    """
    spec = load_openapi(client)
    if not spec:
        return None, []
    paths = spec.get("paths", {})
    method = method.lower()
    for cand in candidates:
        if cand in paths and method in (paths[cand] or {}):
            params = re.findall(r"\{([^}/]+)\}", cand)
            return cand, params
    return None, []

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def ensure(candidate, reason=""):
    if candidate is None:
        pytest.skip(reason)
