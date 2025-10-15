import pytest

TIPOS_VEHICULO = "/tipos/vehiculo"
TIPOS_SERVICIO = "/tipos/servicio"
TIPOS_CONTACTO = "/tipos/contacto"
TIPOS_SERVICIO_POLO = "/tipos/servicio-polo"
ROLES = "/roles"

@pytest.mark.parametrize("path", [TIPOS_VEHICULO, TIPOS_SERVICIO, TIPOS_CONTACTO, TIPOS_SERVICIO_POLO, ROLES])
def test_tipos_catalogos_list(client, path):
    r = client.get(path)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
