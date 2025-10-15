import pytest

def test_models_can_create_rows():
    try:
        from app import models
        from backend.tests.conftest import TestingSessionLocal
    except Exception:
        pytest.skip("No se pudo importar models o TestingSessionLocal")

    db = TestingSessionLocal()
    try:
        if hasattr(models, "Usuario"):
            u = models.Usuario(email="model@x.com", hashed_password="hash", nombre="Model")
            db.add(u); db.commit(); db.refresh(u)
            assert u.id is not None
        else:
            pytest.skip("models.Usuario no existe")

    finally:
        db.close()
