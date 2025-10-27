import io
from typing import Dict, Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.auth import require_public_role
from app.config import get_db


class DummyUser:
    """Usuario mínimo con rol público para usar en las pruebas."""

    def __init__(self) -> None:
        self.id_usuario = 1
        self.roles = [{"tipo_rol": "publico"}]


def _dummy_db() -> Iterator[Dict[str, str]]:
    """Generador simple que simula la dependencia de DB."""
    yield {}


@pytest.fixture(autouse=True)
def override_dependencies():
    """
    Sobrescribe dependencias globales del proyecto para aislar las pruebas.
    """
    app.dependency_overrides[require_public_role] = lambda: DummyUser()
    app.dependency_overrides[get_db] = _dummy_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_dependencies) -> TestClient:
    """Devuelve un TestClient con dependencias sobreescritas."""
    return override_dependencies


@pytest.fixture
def sample_audio_bytes() -> bytes:
    """Audio ficticio en formato bytes para las pruebas."""
    return io.BytesIO(b"fake audio bytes").getvalue()
