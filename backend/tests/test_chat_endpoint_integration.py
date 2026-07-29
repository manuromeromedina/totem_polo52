"""
Tests de integración end-to-end del endpoint HTTP /chat: base de datos real
(sqlite en memoria, con el esquema real de la app) + FastAPI TestClient,
mockeando únicamente la llamada a Gemini (chatbot_service._generate).

A diferencia de test_chat_routes.py (que mockea get_chat_response entero y
solo prueba el "pegamento" de la ruta), acá se ejercita el pipeline real:
parseo de intención -> SQL contra la DB -> armado de la respuesta final.
"""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.config import Base, get_db
from app.main import app
from app.services import chatbot_service


class _FakeResponse:
    def __init__(self, text):
        self.text = text


def _intent_json(**overrides):
    base = {
        "needs_more_info": False,
        "sql_query": "",
        "direct_answer": "",
        "corrected_entity": "",
        "question": "",
    }
    base.update(overrides)
    return json.dumps(base)


@pytest.fixture
def chat_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()
    session.add(
        models.Empresa(
            cuil=1,
            nombre="Logistica Express S.A.",
            rubro="Logistica",
            cant_empleados=30,
            observaciones="",
            fecha_ingreso=date(2020, 1, 1),
            horario_trabajo="8 a 18hs",
            estado=True,
        )
    )
    session.commit()
    session.close()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    original_schema_cache = chatbot_service._schema_cache
    chatbot_service._schema_cache = None

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
    chatbot_service._schema_cache = original_schema_cache
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_chat_endpoint_full_pipeline_returns_data(chat_client, monkeypatch):
    responses = iter(
        [
            _FakeResponse(_intent_json(sql_query="SELECT nombre, rubro FROM empresa")),
            _FakeResponse("Encontré una empresa de logística: Logistica Express S.A."),
        ]
    )
    monkeypatch.setattr(chatbot_service, "_generate", lambda prompt, generation_config: next(responses))

    response = chat_client.post("/chat/", json={"message": "que empresas de logistica hay"})

    assert response.status_code == 200
    body = response.json()
    assert "Logistica Express" in body["reply"]
    assert body["data"] == [{"nombre": "Logistica Express S.A.", "rubro": "Logistica"}]


def test_chat_endpoint_blocks_forbidden_table_end_to_end(chat_client, monkeypatch):
    monkeypatch.setattr(
        chatbot_service,
        "_generate",
        lambda prompt, generation_config: _FakeResponse(_intent_json(sql_query="SELECT * FROM usuario")),
    )

    response = chat_client.post("/chat/", json={"message": "dame los usuarios del sistema"})

    assert response.status_code == 200
    assert response.json()["reply"] == chatbot_service.FORBIDDEN_RESPONSE_TEXT


def test_chat_endpoint_blocks_stacked_injection_end_to_end(chat_client, monkeypatch):
    monkeypatch.setattr(
        chatbot_service,
        "_generate",
        lambda prompt, generation_config: _FakeResponse(
            _intent_json(sql_query="SELECT nombre FROM empresa; DROP TABLE empresa;--")
        ),
    )

    response = chat_client.post("/chat/", json={"message": "dame las empresas"})

    assert response.status_code == 200
    assert response.json()["reply"] == chatbot_service.FORBIDDEN_RESPONSE_TEXT

    # La tabla debe seguir intacta y consultable.
    verify_responses = iter(
        [
            _FakeResponse(_intent_json(sql_query="SELECT nombre FROM empresa")),
            _FakeResponse("Sigue estando Logistica Express S.A."),
        ]
    )
    monkeypatch.setattr(chatbot_service, "_generate", lambda prompt, generation_config: next(verify_responses))
    follow_up = chat_client.post("/chat/", json={"message": "dame las empresas de nuevo"})
    assert follow_up.json()["data"] == [{"nombre": "Logistica Express S.A."}]


def test_chat_endpoint_handles_malformed_model_json_without_500(chat_client, monkeypatch):
    monkeypatch.setattr(
        chatbot_service,
        "_generate",
        lambda prompt, generation_config: _FakeResponse("<<< esto no es JSON >>>"),
    )

    response = chat_client.post("/chat/", json={"message": "algo raro"})

    assert response.status_code == 200
    assert isinstance(response.json()["reply"], str) and response.json()["reply"]


def test_chat_endpoint_handles_gemini_exception_without_500(chat_client, monkeypatch):
    def raising_generate(prompt, generation_config):
        raise RuntimeError("Gemini no responde")

    monkeypatch.setattr(chatbot_service, "_generate", raising_generate)

    response = chat_client.post("/chat/", json={"message": "hola"})

    # get_chat_response ya atrapa el error: el endpoint responde 200 con un
    # mensaje conversacional, no un 500.
    assert response.status_code == 200
    assert isinstance(response.json()["reply"], str) and response.json()["reply"]


def test_chat_endpoint_rejects_missing_message_field(chat_client):
    response = chat_client.post("/chat/", json={})
    assert response.status_code == 422
