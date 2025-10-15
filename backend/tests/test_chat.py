CHAT_PATH = "/chat/"

def test_chat_reply(client):
    r = client.post(CHAT_PATH, json={"message": "Hola"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert any(k in data for k in ("reply", "message", "text"))
