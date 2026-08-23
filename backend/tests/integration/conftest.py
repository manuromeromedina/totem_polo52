"""
Fixtures para pruebas de integración reales: pegan contra la base de
producción (Supabase, la misma DATABASE_URL que usa la app en runtime) en
vez de una sqlite en memoria, para verificar el comportamiento real de la
app incluyendo la conexión, el esquema y RLS.

Seguridad: cada test corre DENTRO de una transacción externa que jamás se
comitea. El código de la app (rutas, servicios) puede llamar a
session.commit() las veces que quiera -- gracias a
`join_transaction_mode="create_savepoint"` esos commits solo liberan un
SAVEPOINT interno, nunca la transacción externa. Al terminar el test se
hace ROLLBACK de esa transacción externa y se cierra la conexión: todo lo
escrito (inserts/updates/deletes) desaparece, la base de producción queda
exactamente como estaba. Este mecanismo se validó manualmente antes de
escribir la suite (ver conversación / historial del proyecto).
"""
import os
import random
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config import engine, get_db
from app.routes.auth import get_current_user
from app import models, services

DATABASE_URL = os.getenv("DATABASE_URL")

requires_real_db = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL no configurada"
)

# app/config.py crea el engine con echo=True (para debug manual); en la
# suite de tests eso solo genera ruido, así que lo apagamos acá.
engine.echo = False


def fake_cuil() -> int:
    """CUIL claramente ficticio (15 digitos) que nunca puede chocar con uno
    real (los CUIL argentinos tienen 11 digitos)."""
    return random.randint(900_000_000_000_000, 999_999_999_999_999)


@pytest.fixture
def real_db_session():
    connection = engine.connect()
    outer_txn = connection.begin()
    TestSessionLocal = sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        outer_txn.rollback()
        connection.close()


@pytest.fixture
def real_client(real_db_session):
    """TestClient conectado a la sesion real-con-rollback. Devuelve
    (client, session) para que el test pueda sembrar datos y verificar
    resultados con la misma sesion que usan las rutas."""

    def override_get_db():
        yield real_db_session

    app.dependency_overrides[get_db] = override_get_db
    # Igual que en tests/test_auth_endpoints.py: sacamos el stub global de
    # get_current_user del conftest raiz para ejercitar la autenticacion
    # real (JWT real, usuario real) en vez de un DummyUser fijo.
    app.dependency_overrides.pop(get_current_user, None)

    client = TestClient(app)
    yield client, real_db_session
    app.dependency_overrides.pop(get_db, None)


def get_or_create_role(session, tipo_rol: str) -> models.Rol:
    role = session.query(models.Rol).filter_by(tipo_rol=tipo_rol).first()
    if role:
        return role
    role = models.Rol(tipo_rol=tipo_rol)
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def create_empresa(session, *, cuil=None, estado=True, **overrides) -> models.Empresa:
    empresa = models.Empresa(
        cuil=cuil or fake_cuil(),
        nombre=overrides.get("nombre", "Empresa Test Integracion"),
        rubro=overrides.get("rubro", "Testing"),
        cant_empleados=overrides.get("cant_empleados", 5),
        observaciones=overrides.get("observaciones", ""),
        fecha_ingreso=overrides.get("fecha_ingreso", date(2024, 1, 1)),
        horario_trabajo=overrides.get("horario_trabajo", "9 a 18"),
        estado=estado,
    )
    session.add(empresa)
    session.commit()
    session.refresh(empresa)
    return empresa


def create_user(
    session,
    *,
    empresa: models.Empresa,
    rol_tipo: str,
    nombre=None,
    email=None,
    password="ClaveSegura1",
    estado=True,
) -> tuple[models.Usuario, str]:
    """Crea un usuario real con contraseña real, ligado a un rol real.
    Devuelve (usuario, password_en_claro) para poder loguearse en el test."""
    suffix = fake_cuil()
    user = models.Usuario(
        nombre=nombre or f"test_{suffix}",
        email=email or f"test_{suffix}@example.com",
        contrasena=services.hash_password(password),
        estado=estado,
        fecha_registro=date.today(),
        cuil=empresa.cuil,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    role = get_or_create_role(session, rol_tipo)
    session.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    session.commit()

    return user, password


def login(client, nombre: str, password: str) -> str:
    """Hace login real via /login y devuelve el access_token."""
    response = client.post("/login", data={"username": nombre, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
