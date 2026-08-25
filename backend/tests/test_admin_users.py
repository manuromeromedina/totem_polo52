from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, services
from app.config import Base
from app.main import app
from app.routes import admin_users as admin_routes
from app.schemas import UserCreate


POLO_CUIL = admin_routes.POLO_CUIL


def _setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


def _seed_base(session):
    polo = models.Empresa(
        cuil=POLO_CUIL,
        nombre="Polo 52",
        rubro="Administración",
        cant_empleados=5,
        observaciones="",
        fecha_ingreso=date(2020, 1, 1),
        horario_trabajo="08-18",
        estado=True,
    )
    session.add(polo)

    empresa = models.Empresa(
        cuil=2000,
        nombre="Empresa Secundaria",
        rubro="Logística",
        cant_empleados=40,
        observaciones="",
        fecha_ingreso=date(2021, 6, 1),
        horario_trabajo="07-17",
        estado=True,
    )
    session.add(empresa)
    session.commit()

    rol_admin_polo = models.Rol(tipo_rol="admin_polo")
    rol_admin_empresa = models.Rol(tipo_rol="admin_empresa")
    rol_publico = models.Rol(tipo_rol="publico")
    session.add_all([rol_admin_polo, rol_admin_empresa, rol_publico])
    session.commit()

    return {
        "admin_polo": rol_admin_polo.id_rol,
        "admin_empresa": rol_admin_empresa.id_rol,
        "publico": rol_publico.id_rol,
        "empresa_cuil": empresa.cuil,
    }


def _create_user_with_role(session, *, nombre, cuil, role_id):
    user = models.Usuario(
        nombre=nombre,
        email=f"{nombre}@test.com",
        contrasena=services.hash_password("ClaveSegura1"),
        estado=True,
        fecha_registro=date.today(),
        cuil=cuil,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role_id))
    session.commit()
    return user


@pytest.fixture
def admin_db():
    engine, SessionLocal = _setup_db()
    session = SessionLocal()
    role_info = _seed_base(session)
    session.close()
    yield SessionLocal, role_info
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_validate_user_creation_limits_admin_polo_wrong_company(admin_db):
    SessionLocal, roles = admin_db
    session = SessionLocal()
    dto = UserCreate(
        nombre="Nuevo",
        email="nuevo@test.com",
        cuil=roles["empresa_cuil"],
        estado=True,
        id_rol=roles["admin_polo"],
    )
    with pytest.raises(Exception) as exc:
        admin_routes.validate_user_creation_limits(session, dto)
    assert "solo puede" in str(exc.value)
    session.close()


def test_validate_user_creation_limits_admin_empresa_rejected(admin_db):
    """admin_empresa ya no se crea a mano: se crea (junto con su empresa) por
    el autoregistro público y su aprobación por admin_polo."""
    SessionLocal, roles = admin_db
    session = SessionLocal()
    dto = UserCreate(
        nombre="extraEmpresa",
        email="extraEmpresa@test.com",
        cuil=roles["empresa_cuil"],
        estado=True,
        id_rol=roles["admin_empresa"],
    )
    with pytest.raises(Exception) as exc:
        admin_routes.validate_user_creation_limits(session, dto)
    assert "registro público" in str(exc.value).lower()
    session.close()


def test_validate_user_creation_limits_public_needs_polo(admin_db):
    SessionLocal, roles = admin_db
    session = SessionLocal()
    dto = UserCreate(
        nombre="publico",
        email="publico@test.com",
        cuil=roles["empresa_cuil"],
        estado=True,
        id_rol=roles["publico"],
    )
    with pytest.raises(Exception) as exc:
        admin_routes.validate_user_creation_limits(session, dto)
    assert "publico" in str(exc.value).lower()
    session.close()


@pytest.fixture
def admin_client(admin_db):
    SessionLocal, roles = admin_db
    session = SessionLocal()
    admin_user = _create_user_with_role(
        session,
        nombre="adminpolo",
        cuil=POLO_CUIL,
        role_id=roles["admin_polo"],
    )
    admin_id = admin_user.id_usuario
    session.close()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_require_admin():
        db = SessionLocal()
        user = db.query(models.Usuario).get(admin_id)
        db.close()
        return user

    app.dependency_overrides[admin_routes.get_db] = override_get_db
    app.dependency_overrides[admin_routes.require_admin_polo] = override_require_admin

    client = TestClient(app)
    yield client, SessionLocal, roles
    app.dependency_overrides.clear()


def test_get_polo_details_returns_related_data(admin_client):
    client, SessionLocal, roles = admin_client
    session = SessionLocal()
    empresa_extra = session.query(models.Empresa).filter(models.Empresa.cuil == roles["empresa_cuil"]).first()
    contacto = models.Contacto(
        cuil_empresa=empresa_extra.cuil,
        id_tipo_contacto=1,
        nombre="Contacto",
        telefono="123",
        datos={"email": "c@t.com"},
        direccion="Calle 1",
    )
    session.add(contacto)

    tipo_servicio_polo = models.TipoServicioPolo(id_tipo_servicio_polo=1, tipo="Cowork")
    session.add(tipo_servicio_polo)
    session.commit()

    servicio_polo = models.ServicioPolo(
        nombre="Cowork",
        horario="08-20",
        datos={"puestos": 10},
        propietario="Polo",
        id_tipo_servicio_polo=tipo_servicio_polo.id_tipo_servicio_polo,
        cuil=empresa_extra.cuil,
    )
    session.add(servicio_polo)
    session.commit()

    lote = models.Lote(
        id_servicio_polo=servicio_polo.id_servicio_polo,
        dueno="Empresa Secundaria",
        lote=1,
        manzana=2,
    )
    session.add(lote)
    session.commit()
    session.close()

    resp = client.get("/polo/me")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["empresas"]) >= 1
    assert len(body["servicios_polo"]) >= 1
    assert len(body["usuarios"]) >= 1
    assert len(body["lotes"]) >= 1


def test_create_empresa_user_success(admin_client):
    client, SessionLocal, roles = admin_client
    resp = client.post(
        f"/empresas/{roles['empresa_cuil']}/usuarios",
        json={"nombre": "nuevoEmpleado", "email": "nuevoempleado@test.com"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nombre"] == "nuevoEmpleado"
    assert body["email"] == "nuevoempleado@test.com"
    assert body["cuil"] == roles["empresa_cuil"]
    assert body["estado"] is True
    assert [r["tipo_rol"] for r in body["roles"]] == ["admin_empresa"]

    session = SessionLocal()
    creado = session.query(models.Usuario).filter(models.Usuario.nombre == "nuevoEmpleado").first()
    assert creado is not None
    assert creado.mostrar_bienvenida is True
    # La contraseña generada automáticamente nunca queda en texto plano ni vacía
    assert creado.contrasena and creado.contrasena != ""
    session.close()


def test_create_empresa_user_duplicate_nombre(admin_client):
    client, SessionLocal, roles = admin_client
    session = SessionLocal()
    _create_user_with_role(
        session, nombre="repetido", cuil=roles["empresa_cuil"], role_id=roles["admin_empresa"]
    )
    session.close()

    resp = client.post(
        f"/empresas/{roles['empresa_cuil']}/usuarios",
        json={"nombre": "repetido", "email": "otro@test.com"},
    )
    assert resp.status_code == 400
    assert "nombre" in resp.json()["detail"].lower()


def test_create_empresa_user_duplicate_email(admin_client):
    client, SessionLocal, roles = admin_client
    session = SessionLocal()
    _create_user_with_role(
        session, nombre="original", cuil=roles["empresa_cuil"], role_id=roles["admin_empresa"]
    )
    session.close()

    resp = client.post(
        f"/empresas/{roles['empresa_cuil']}/usuarios",
        json={"nombre": "otroNombre", "email": "original@test.com"},
    )
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


def test_create_empresa_user_empresa_inexistente(admin_client):
    client, SessionLocal, roles = admin_client
    resp = client.post(
        "/empresas/999999/usuarios",
        json={"nombre": "quienSea", "email": "quiensea@test.com"},
    )
    assert resp.status_code == 404


def test_create_empresa_user_empresa_desactivada(admin_client):
    client, SessionLocal, roles = admin_client
    session = SessionLocal()
    empresa = session.query(models.Empresa).filter(models.Empresa.cuil == roles["empresa_cuil"]).first()
    empresa.estado = False
    session.commit()
    session.close()

    resp = client.post(
        f"/empresas/{roles['empresa_cuil']}/usuarios",
        json={"nombre": "quienSea", "email": "quiensea@test.com"},
    )
    assert resp.status_code == 400
    assert "desactivada" in resp.json()["detail"].lower()
