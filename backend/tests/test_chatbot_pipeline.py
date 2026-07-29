"""
Tests de integración de get_chat_response(): arman el pipeline completo
(intención -> SQL -> respuesta final) contra una base sqlite en memoria,
mockeando únicamente la llamada a Gemini (chatbot_service._generate).
"""
import json

import pytest
from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.orm import sessionmaker

from app.services import chatbot_service
from app.services.common import GENERIC_ERROR_MESSAGE


class _FakeResponse:
    def __init__(self, text):
        self.text = text


@pytest.fixture(autouse=True)
def reset_schema_cache():
    """Evita que el esquema cacheado de otro test/DB se filtre acá."""
    original = chatbot_service._schema_cache
    chatbot_service._schema_cache = None
    yield
    chatbot_service._schema_cache = original


@pytest.fixture
def empresa_db():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    with engine.begin() as conn:
        conn.execute(sa_text("CREATE TABLE empresa (cuil INTEGER PRIMARY KEY, nombre TEXT, rubro TEXT)"))
        conn.execute(
            sa_text("INSERT INTO empresa (cuil, nombre, rubro) VALUES (1, 'Logistica Express S.A.', 'Logistica')")
        )
    db = SessionLocal()
    yield db
    db.close()


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


def test_greeting_returns_direct_answer_without_second_call(empresa_db, monkeypatch):
    calls = []

    def fake_generate(prompt, generation_config):
        calls.append(prompt)
        return _FakeResponse(_intent_json(direct_answer="¡Hola! Soy POLO, ¿en qué te ayudo?"))

    monkeypatch.setattr(chatbot_service, "_generate", fake_generate)

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "hola")

    assert text_reply == "¡Hola! Soy POLO, ¿en qué te ayudo?"
    assert data == []
    assert len(calls) == 1  # un saludo no debe disparar la segunda llamada (respuesta final)


def test_needs_more_info_returns_question_without_db_access(empresa_db, monkeypatch):
    monkeypatch.setattr(
        chatbot_service,
        "_generate",
        lambda prompt, generation_config: _FakeResponse(
            _intent_json(needs_more_info=True, question="¿De qué empresa querés saber?")
        ),
    )
    monkeypatch.setattr(
        chatbot_service,
        "execute_sql_query",
        lambda db, query: pytest.fail("no debería ejecutar SQL si falta información"),
    )

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "dame el telefono")
    assert text_reply == "¿De qué empresa querés saber?"
    assert data == []


def test_data_query_executes_sql_and_returns_final_text(empresa_db, monkeypatch):
    responses = iter(
        [
            _FakeResponse(_intent_json(sql_query="SELECT nombre, rubro FROM empresa")),
            _FakeResponse("En el parque hay una empresa de logística: Logistica Express S.A."),
        ]
    )
    monkeypatch.setattr(chatbot_service, "_generate", lambda prompt, generation_config: next(responses))

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "que empresas de logistica hay")

    assert "Logistica Express" in text_reply
    assert data == [{"nombre": "Logistica Express S.A.", "rubro": "Logistica"}]


def test_forbidden_table_blocks_before_executing_sql(empresa_db, monkeypatch):
    monkeypatch.setattr(
        chatbot_service,
        "_generate",
        lambda prompt, generation_config: _FakeResponse(
            _intent_json(sql_query="SELECT * FROM usuario")
        ),
    )
    monkeypatch.setattr(
        chatbot_service,
        "execute_sql_query",
        lambda db, query: pytest.fail("no debería ejecutar una consulta sobre una tabla prohibida"),
    )

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "dame los usuarios")
    assert text_reply == chatbot_service.FORBIDDEN_RESPONSE_TEXT
    assert data == []


def test_non_select_query_is_rejected_and_data_untouched(empresa_db, monkeypatch):
    """
    Si el modelo alucina un DELETE/UPDATE sobre una tabla permitida (no está
    en FORBIDDEN_SQL_TABLES), is_sql_query_allowed igual debe rechazarlo por
    no ser un SELECT, sin que execute_sql_query llegue a ejecutarse.
    """
    monkeypatch.setattr(
        chatbot_service,
        "_generate",
        lambda prompt, generation_config: _FakeResponse(
            _intent_json(sql_query="DELETE FROM empresa WHERE cuil = 1")
        ),
    )
    monkeypatch.setattr(
        chatbot_service,
        "execute_sql_query",
        lambda db, query: pytest.fail("un DELETE nunca debería llegar a ejecutarse"),
    )

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "borra la empresa 1")

    assert text_reply == chatbot_service.FORBIDDEN_RESPONSE_TEXT
    row = empresa_db.execute(sa_text("SELECT COUNT(*) FROM empresa WHERE cuil = 1")).scalar()
    assert row == 1  # la fila sigue existiendo, el DELETE nunca corrió


def test_stacked_statement_injection_is_rejected_before_execution(empresa_db, monkeypatch):
    """
    Prompt injection clásico: el modelo devuelve un SELECT legítimo seguido
    de un DROP TABLE apilado con ";". Debe bloquearse antes de tocar la DB.
    """
    monkeypatch.setattr(
        chatbot_service,
        "_generate",
        lambda prompt, generation_config: _FakeResponse(
            _intent_json(sql_query="SELECT nombre FROM empresa; DROP TABLE empresa;--")
        ),
    )
    monkeypatch.setattr(
        chatbot_service,
        "execute_sql_query",
        lambda db, query: pytest.fail("una sentencia apilada nunca debería llegar a ejecutarse"),
    )

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "dame las empresas")

    assert text_reply == chatbot_service.FORBIDDEN_RESPONSE_TEXT
    row = empresa_db.execute(
        sa_text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='empresa'")
    ).scalar()
    assert row == 1  # la tabla sigue existiendo


def test_no_results_still_lets_gemini_phrase_the_final_answer(empresa_db, monkeypatch):
    """
    Sin resultados, el pipeline ya no corta con un mensaje fijo por código:
    igual llama a Gemini (que ya tiene instrucciones para ese caso) y confía
    en su respuesta, para que suene natural en vez de una frase enlatada.
    """
    responses = iter(
        [
            _FakeResponse(_intent_json(sql_query="SELECT nombre FROM empresa WHERE rubro = 'inexistente'")),
            _FakeResponse("No tengo empresas de ese rubro registradas, pero puedo contarte sobre logística si te sirve."),
        ]
    )
    monkeypatch.setattr(chatbot_service, "_generate", lambda prompt, generation_config: next(responses))

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "empresas de rubro inexistente")

    assert text_reply == "No tengo empresas de ese rubro registradas, pero puedo contarte sobre logística si te sirve."
    assert data == []


def test_intent_parse_failure_falls_back_gracefully_without_retry_call(empresa_db, monkeypatch):
    calls = []

    def fake_generate(prompt, generation_config):
        calls.append(prompt)
        return _FakeResponse("esto no es JSON para nada")

    monkeypatch.setattr(chatbot_service, "_generate", fake_generate)

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "algo raro")

    assert isinstance(text_reply, str) and text_reply
    assert data == []
    # Optimización de latencia: ya no se reintenta con una segunda llamada a Gemini.
    assert len(calls) == 1


def test_generate_exception_on_intent_stage_degrades_gracefully(empresa_db, monkeypatch):
    """
    Si Gemini falla ya en la etapa de intención (ej. timeout), el pipeline no
    debe propagar la excepción: debe devolver un mensaje conversacional.
    """
    def raising_generate(prompt, generation_config):
        raise RuntimeError("timeout hablando con Gemini")

    monkeypatch.setattr(chatbot_service, "_generate", raising_generate)

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "hola")
    assert isinstance(text_reply, str) and text_reply
    assert data == []


def test_unexpected_error_outside_gemini_returns_generic_message(empresa_db, monkeypatch):
    """Un fallo inesperado fuera de las llamadas a Gemini (ej. al leer el esquema) sí usa el mensaje genérico."""
    def raising_schema(db, force_refresh=False):
        raise RuntimeError("la base no responde")

    monkeypatch.setattr(chatbot_service, "get_database_schema", raising_schema)

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "hola")
    assert text_reply == GENERIC_ERROR_MESSAGE
    assert data == []
    assert corrected is None


def test_final_stage_exception_falls_back_to_local_composition(empresa_db, monkeypatch):
    responses = iter(
        [
            _FakeResponse(_intent_json(sql_query="SELECT nombre, rubro FROM empresa")),
        ]
    )

    def fake_generate(prompt, generation_config):
        try:
            return next(responses)
        except StopIteration:
            raise RuntimeError("Gemini caído en la etapa final")

    monkeypatch.setattr(chatbot_service, "_generate", fake_generate)

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "que empresas de logistica hay")

    assert "Logistica Express" in text_reply  # viene de compose_fallback_response, no de Gemini
    assert data


def test_final_answer_from_gemini_is_trusted_even_if_it_sounds_negative(empresa_db, monkeypatch):
    """
    Ya no hay código que reescriba lo que Gemini responde por pattern-matching
    de frases. Si el modelo, con criterio propio, dice que no hay datos pese a
    haber resultados (caso raro), se confía en su respuesta tal cual: la
    decisión de qué decir es del modelo, no del código.
    """
    responses = iter(
        [
            _FakeResponse(_intent_json(sql_query="SELECT nombre, rubro FROM empresa")),
            _FakeResponse("No encontré información sobre eso en la base de datos."),
        ]
    )
    monkeypatch.setattr(chatbot_service, "_generate", lambda prompt, generation_config: next(responses))

    text_reply, data, corrected = chatbot_service.get_chat_response(empresa_db, "que empresas de logistica hay")

    assert text_reply == "No encontré información sobre eso en la base de datos."
    assert data  # los datos igual viajan en la respuesta, aunque el texto no los mencione


def test_final_prompt_leaves_tone_and_format_to_the_model(empresa_db, monkeypatch):
    """
    El prompt final solo fija las reglas de seguridad/alcance (no datos
    sensibles, no temas ajenos al parque); el tono y formato quedan a
    criterio del modelo, no dictados línea por línea desde el código.
    """
    captured_prompts = []

    def fake_generate(prompt, generation_config):
        captured_prompts.append(prompt)
        if len(captured_prompts) == 1:
            return _FakeResponse(_intent_json(sql_query="SELECT nombre, rubro FROM empresa"))
        return _FakeResponse("Respuesta corta.")

    monkeypatch.setattr(chatbot_service, "_generate", fake_generate)
    chatbot_service.get_chat_response(empresa_db, "que empresas de logistica hay")

    final_prompt = captured_prompts[1]
    assert "usá tu propio criterio" in final_prompt.lower()
    assert "CUIL" in final_prompt  # la única regla dura que se mantiene: nunca exponer datos sensibles
