import io
from typing import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.auth import get_current_user
from app.config import get_db
from app.rate_limit import reset_rate_limits


class DummyUser:
    """Usuario mínimo con rol público para usar en las pruebas."""

    def __init__(self) -> None:
        self.id_usuario = 1
        self.roles = [{"tipo_rol": "publico"}]


def _dummy_db() -> Iterator[MagicMock]:
    """Simula la dependencia de DB: acepta add/commit/query/execute como no-ops,
    ya que las pruebas mockean la lógica real vía app.routes.*.services.*."""
    yield MagicMock()


@pytest.fixture(autouse=True)
def override_dependencies():
    """
    Sobrescribe dependencias globales del proyecto para aislar las pruebas.
    """
    app.dependency_overrides[get_current_user] = lambda: DummyUser()
    app.dependency_overrides[get_db] = _dummy_db
    reset_rate_limits()
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    reset_rate_limits()


@pytest.fixture
def client(override_dependencies) -> TestClient:
    """Devuelve un TestClient con dependencias sobreescritas."""
    return override_dependencies


@pytest.fixture
def sample_audio_bytes() -> bytes:
    """Audio ficticio en formato bytes para las pruebas."""
    return io.BytesIO(b"fake audio bytes").getvalue()
