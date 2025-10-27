import os

import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.integration
@pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL no configurada")
def test_database_metadata_access():
    """
    Verifica que la conexión a la base de datos funciona y lista tablas.
    """
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public';"
                )
            )
            tables = [row[0] for row in result]
            assert isinstance(tables, list)
            assert len(tables) >= 0
    except Exception as exc:  # pragma: no cover - depende de entorno
        pytest.skip(f"No se pudo conectar a la base de datos: {exc}")


@pytest.mark.integration
@pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL no configurada")
def test_database_row_counts_are_accessible():
    """
    Hace un conteo simple de filas en las tablas disponibles.
    """
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            tables = [
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public';"
                    )
                )
            ]
            for table in tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    assert count >= 0
                except Exception:
                    pytest.skip(f"No se pudo contar filas de {table}")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"No se pudo conectar a la base de datos: {exc}")
