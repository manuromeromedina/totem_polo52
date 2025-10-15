# backend/tests/test__debug_paths.py  (temporal)
def test_print_paths(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = list(r.json().get("paths", {}).keys())
    print("\n\n== PATHS ==\n" + "\n".join(paths) + "\n")
