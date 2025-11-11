from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, services
from app.config import Base
from app.routes import auth as auth_routes
from app.schemas import ChangePasswordDirect


def _setup_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


@pytest.fixture
def change_pw_context():
    engine, SessionLocal = _setup_engine()
    session = SessionLocal()

    empresa = models.Empresa(
        cuil=1234,
        nombre="Empresa Test",
        rubro="Servicios",
        cant_empleados=20,
        observaciones="",
        fecha_ingreso=date(2020, 1, 1),
        horario_trabajo="08-17",
        estado=True,
    )
    session.add(empresa)
    session.commit()

    user = models.Usuario(
        nombre="usuario_test",
        email="usuario@test.com",
        contrasena=services.hash_password("ClaveActual1"),
        estado=True,
        fecha_registro=date.today(),
        cuil=empresa.cuil,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    yield session, user

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def mute_change_pw_emails(monkeypatch):
    monkeypatch.setattr(auth_routes, "_send_change_password_success_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth_routes, "_send_change_password_failure_email", lambda *args, **kwargs: None)
    auth_routes._change_pw_attempts.clear()
    yield
    auth_routes._change_pw_attempts.clear()


def test_change_password_direct_success(change_pw_context):
    session, user = change_pw_context
    dto = ChangePasswordDirect(current_password="ClaveActual1", new_password="NuevaClave1", confirm_password="NuevaClave1")

    result = auth_routes.change_password_direct(dto, current_user=user, db=session)

    assert result["success"] is True
    session.refresh(user)
    assert services.verify_password("NuevaClave1", user.contrasena)


def test_change_password_direct_rejects_wrong_current(change_pw_context):
    session, user = change_pw_context
    dto = ChangePasswordDirect(current_password="ClaveIncorrecta", new_password="NuevaClave1", confirm_password="NuevaClave1")

    result = auth_routes.change_password_direct(dto, current_user=user, db=session)

    assert result["success"] is False
    assert result["wrong_current"] is True
    assert "incorrecta" in result["error"].lower()


def test_change_password_direct_blocks_reused_password(change_pw_context):
    session, user = change_pw_context
    reused_hash = services.hash_password("Historial123")
    services.save_password_to_history(session, user.id_usuario, reused_hash)
    session.commit()

    dto = ChangePasswordDirect(current_password="ClaveActual1", new_password="Historial123", confirm_password="Historial123")

    result = auth_routes.change_password_direct(dto, current_user=user, db=session)

    assert result["success"] is False
    assert result["password_reused"] is True


def test_change_password_direct_enforces_cooldown(change_pw_context):
    session, user = change_pw_context
    dto = ChangePasswordDirect(current_password="Invalida", new_password="NuevaClave1", confirm_password="NuevaClave1")

    for attempt in range(auth_routes._MAX_FAILS_CHANGE_PW):
        res = auth_routes.change_password_direct(dto, current_user=user, db=session)
        assert res["success"] is False
        if attempt < auth_routes._MAX_FAILS_CHANGE_PW - 1:
            assert res.get("locked") in (False, None)
        else:
            assert res.get("locked") is True

    locked_response = auth_routes.change_password_direct(dto, current_user=user, db=session)
    assert locked_response["success"] is False
    assert locked_response["locked"] is True
    assert "demasiados" in locked_response["error"].lower()
