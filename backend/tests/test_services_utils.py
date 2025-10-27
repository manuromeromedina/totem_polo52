from datetime import datetime, timedelta

import pytest
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app import services
from app.config import SECRET_KEY, ALGORITHM


def test_hash_and_verify_password():
    raw_password = "ClaveSegura123!"
    hashed = services.hash_password(raw_password)
    assert hashed != raw_password
    assert services.verify_password(raw_password, hashed) is True
    assert services.verify_password("otra", hashed) is False


def test_generate_random_password_has_minimum_requirements():
    password = services.generate_random_password(12)
    assert len(password) == 12
    assert any(c.islower() for c in password)
    assert any(c.isupper() for c in password)
    assert any(c.isdigit() for c in password)
    assert any(c in "!@#$%&*" for c in password)


def test_create_access_token_contains_subject():
    payload = {"sub": "usuario_test"}
    token = services.create_access_token(payload, expires_delta=timedelta(minutes=5))
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "usuario_test"
    assert "exp" in decoded


def test_normalize_text_removes_accents():
    text_input = "ÁRBOL Ñandú"
    assert services.normalize_text(text_input) == "arbol nandu"


def test_execute_sql_query_allows_select_only():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE empresa (id INTEGER PRIMARY KEY, nombre TEXT)"))
        connection.execute(text("INSERT INTO empresa (nombre) VALUES ('Polo 52')"))

    db: Session = SessionLocal()
    try:
        results = services.execute_sql_query(db, "SELECT nombre FROM empresa")
        assert results == [{"nombre": "Polo 52"}]

        non_select = services.execute_sql_query(db, "DELETE FROM empresa")
        assert "Solo se permiten consultas SELECT." in non_select[0]["error"]
    finally:
        db.close()


def test_transcribe_audio_raises_when_not_configured():
    original_provider = services.VOICE_PROVIDER
    original_client = services.speech_client
    services.VOICE_PROVIDER = None
    services.speech_client = None
    with pytest.raises(services.HTTPException) as exc:
        services.transcribe_audio(b"bytes")
    assert exc.value.status_code == 503
    services.VOICE_PROVIDER = original_provider
    services.speech_client = original_client


def test_text_to_speech_rejects_unknown_provider():
    with pytest.raises(services.HTTPException):
        services.text_to_speech("hola", voice_provider="otro")
