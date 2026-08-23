"""
Smoke test del harness de integracion real (ver conftest.py). Si esto no
pasa, NO hay que confiar en el resto de la suite de tests/integration/.
"""
import pytest
from sqlalchemy import text

from tests.integration.conftest import (
    requires_real_db,
    create_empresa,
    create_user,
    login,
    auth_headers,
)


@requires_real_db
def test_real_login_and_authenticated_call_roundtrip(real_client):
    client, session = real_client
    empresa = create_empresa(session, nombre="Smoke Test Empresa")
    user, password = create_user(session, empresa=empresa, rol_tipo="publico")

    token = login(client, user.nombre, password)
    response = client.get("/tipos/vehiculo", headers=auth_headers(token))
    assert response.status_code == 200

    # El insert del smoke test tiene que ser visible DENTRO de la misma
    # transaccion del test (si esto fallara, el harness no serviria para
    # nada: no estariamos probando lo que la app realmente hace).
    found = session.execute(
        text("SELECT cuil FROM empresa WHERE cuil = :cuil"), {"cuil": empresa.cuil}
    ).scalar()
    assert found == empresa.cuil


@requires_real_db
def test_marker_from_previous_test_never_leaked_to_production(real_client):
    """
    Corre en una sesion NUEVA (transaccion NUEVA) y verifica que la empresa
    creada en el test anterior no exista. Si este test fallara, hay que
    dejar de usar el harness contra produccion inmediatamente.
    """
    client, session = real_client
    from sqlalchemy import text as _text

    leaked = session.execute(
        _text("SELECT COUNT(*) FROM empresa WHERE nombre = 'Smoke Test Empresa'")
    ).scalar()
    assert leaked == 0
