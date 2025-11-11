from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, services
from app.config import Base
from app.main import app
from app.routes import company_user as company_routes


def _setup_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


def _seed_base(db):
    empresa = models.Empresa(
        cuil=1010,
        nombre="Empresa Uno",
        rubro="Servicios",
        cant_empleados=20,
        observaciones="",
        fecha_ingreso=date(2022, 1, 1),
        horario_trabajo="08-18",
        estado=True,
    )
    db.add(empresa)
    db.commit()

    user = models.Usuario(
        nombre="empresa_admin",
        email="admin@empresa.com",
        contrasena=services.hash_password("Clave123!"),
        estado=True,
        fecha_registro=date.today(),
        cuil=empresa.cuil,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    role = models.Rol(tipo_rol="admin_empresa")
    db.add(role)
    db.commit()
    db.refresh(role)

    db.add(models.RolUsuario(id_usuario=user.id_usuario, id_rol=role.id_rol))
    db.commit()

    tipo_vehiculo = models.TipoVehiculo(id_tipo_vehiculo=1, tipo="Corporativo")
    db.add(tipo_vehiculo)
    db.commit()

    tipo_servicio = models.TipoServicio(id_tipo_servicio=1, tipo="Soporte")
    db.add(tipo_servicio)
    db.commit()

    tipo_contacto = models.TipoContacto(id_tipo_contacto=1, tipo="Administrativo")
    db.add(tipo_contacto)
    db.commit()

    return user


@pytest.fixture
def company_client(monkeypatch):
    engine, SessionLocal = _setup_engine()
    db = SessionLocal()
    user = _seed_base(db)
    user_data = {"id_usuario": user.id_usuario}
    db.close()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        session = SessionLocal()
        usr = session.query(models.Usuario).filter(models.Usuario.id_usuario == user_data["id_usuario"]).first()
        session.close()
        return usr

    app.dependency_overrides[company_routes.get_db] = override_get_db
    app.dependency_overrides[company_routes.get_current_user] = override_current_user
    app.dependency_overrides[company_routes.require_empresa_role] = override_current_user

    client = TestClient(app)

    yield client, SessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_update_password_prevents_reuse(company_client):
    client, SessionLocal = company_client
    session = SessionLocal()
    user = session.query(models.Usuario).first()
    services.save_password_to_history(session, user.id_usuario, user.contrasena)
    session.commit()
    session.close()

    response = client.put(
        "/update_password",
        json={"password": "Clave123!"},
    )

    assert response.status_code == 400
    assert "ya hayas utilizado" in response.json()["detail"].lower()


def test_create_and_update_vehicle(company_client):
    client, SessionLocal = company_client
    veh_payload = {
        "id_tipo_vehiculo": 1,
        "horarios": "06-18",
        "frecuencia": "Diaria",
        "datos": {"cantidad": 2, "patente": "AB123CD", "carga": "mediana"},
    }
    create_resp = client.post("/vehiculos", json=veh_payload)
    assert create_resp.status_code == 200
    veh_id = create_resp.json()["id_vehiculo"]

    update_payload = {
        "id_tipo_vehiculo": 1,
        "horarios": "07-19",
        "frecuencia": "Semanal",
        "datos": {"cantidad": 1, "patente": "CD321BA", "carga": "alta"},
    }
    update_resp = client.put(f"/vehiculos/{veh_id}", json=update_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["horarios"] == "07-19"


def test_create_servicio_and_delete(company_client):
    client, SessionLocal = company_client
    service_payload = {"datos": {"detalle": "Mesa de ayuda"}, "id_tipo_servicio": 1}
    create_resp = client.post("/servicios", json=service_payload)
    assert create_resp.status_code == 200
    service_id = create_resp.json()["id_servicio"]

    delete_resp = client.delete(f"/servicios/{service_id}")
    assert delete_resp.status_code == 204


def test_create_and_update_contact(company_client):
    client, SessionLocal = company_client
    contact_payload = {
        "id_tipo_contacto": 1,
        "nombre": "Contacto",
        "telefono": "123",
        "datos": {"email": "contato@test.com"},
        "direccion": "Calle 123",
    }
    create_resp = client.post("/contactos", json=contact_payload)
    assert create_resp.status_code == 200
    contact_id = create_resp.json()["id_contacto"]

    contact_payload["telefono"] = "999"
    update_resp = client.put(f"/contactos/{contact_id}", json=contact_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["telefono"] == "999"
