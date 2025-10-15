SEARCH_ALL = "/search"
SEARCH_CONTACTOS = "/search/contactos"
SEARCH_LOTES = "/search/lotes"

def test_search_root(client):
    r = client.get(SEARCH_ALL, params={"q": "test"})
    assert r.status_code == 200

def test_search_contactos(client):
    r = client.get(SEARCH_CONTACTOS, params={"q": "test"})
    assert r.status_code == 200

def test_search_lotes(client):
    r = client.get(SEARCH_LOTES, params={"q": "test"})
    assert r.status_code == 200
