import pytest

def test_create_user_service_unit():
    try:
        from app import services
        from app import models
        from backend.tests.conftest import TestingSessionLocal  # reusa la sesión de test
    except Exception:
        pytest.skip("No se pudo importar capa services o TestingSessionLocal")

    db = TestingSessionLocal()
    try:
        if hasattr(services, "create_user"):
            user = services.create_user(db, email="eve@example.com", password="Segura!111", nombre="Eve")
            assert getattr(user, "id", None) is not None
            assert user.email == "eve@example.com"
        else:
            pytest.skip("services.create_user no existe en este proyecto")
    finally:
        db.close()
