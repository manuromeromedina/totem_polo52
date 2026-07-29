"""
Tests unitarios de las piezas puras del pipeline del chatbot:
validación SQL, parseo de intención, extracción de texto de Gemini,
cache del esquema de la base y el dispatcher resiliente de modelos.
"""
from datetime import date

import pytest

from app.services import chatbot_service


# ═══════════════════════════════════════════════════════════════════
# is_sql_query_allowed
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "query",
    [
        "SELECT nombre, rubro FROM empresa WHERE rubro ILIKE '%logistica%'",
        "SELECT nombre FROM contacto",
        "select nombre from servicio_polo",
    ],
)
def test_is_sql_query_allowed_accepts_permitted_tables(query):
    assert chatbot_service.is_sql_query_allowed(query) is True


@pytest.mark.parametrize("table", sorted(chatbot_service.FORBIDDEN_SQL_TABLES))
def test_is_sql_query_allowed_blocks_every_forbidden_table(table):
    assert chatbot_service.is_sql_query_allowed(f"SELECT * FROM {table}") is False
    # También debe bloquear con comillas y mayúsculas mezcladas.
    assert chatbot_service.is_sql_query_allowed(f'SELECT * FROM "{table.upper()}"') is False


def test_is_sql_query_allowed_rejects_empty_query():
    assert chatbot_service.is_sql_query_allowed("") is False
    assert chatbot_service.is_sql_query_allowed(None) is False


def test_is_sql_query_allowed_does_not_false_positive_on_substrings():
    # "servicio_polo" contiene "servicio" (tabla prohibida) como substring,
    # pero es una tabla distinta y permitida: no debe bloquearse.
    assert chatbot_service.is_sql_query_allowed("SELECT * FROM servicio_polo") is True


@pytest.mark.parametrize(
    "query",
    [
        "SELECT nombre FROM empresa; DROP TABLE empresa;--",
        "SELECT nombre FROM empresa; DELETE FROM empresa",
        "SELECT 1; COMMIT; DROP TABLE empresa;",
    ],
)
def test_is_sql_query_allowed_blocks_stacked_statements(query):
    """Defensa en profundidad contra prompt injection que intente apilar sentencias."""
    assert chatbot_service.is_sql_query_allowed(query) is False


def test_is_sql_query_allowed_allows_single_trailing_semicolon():
    assert chatbot_service.is_sql_query_allowed("SELECT nombre FROM empresa;") is True


@pytest.mark.parametrize(
    "query",
    [
        "SELECT nombre FROM empresa -- ' OR 1=1",
        "SELECT nombre FROM empresa /* comentario */",
    ],
)
def test_is_sql_query_allowed_blocks_sql_comments(query):
    assert chatbot_service.is_sql_query_allowed(query) is False


@pytest.mark.parametrize(
    "keyword",
    ["insert", "update", "delete", "drop", "alter", "truncate", "grant", "create"],
)
def test_is_sql_query_allowed_blocks_dml_ddl_keywords(keyword):
    assert chatbot_service.is_sql_query_allowed(f"SELECT * FROM empresa WHERE {keyword} = 1") is False


def test_is_sql_query_allowed_rejects_non_select_statements():
    assert chatbot_service.is_sql_query_allowed("DELETE FROM empresa") is False
    assert chatbot_service.is_sql_query_allowed("UPDATE empresa SET nombre = 'x'") is False


# ═══════════════════════════════════════════════════════════════════
# parse_intent_json
# ═══════════════════════════════════════════════════════════════════


class _FakeResponse:
    def __init__(self, text=None, candidates=None, raise_on_text=False):
        self._text = text
        self.candidates = candidates or []
        self._raise_on_text = raise_on_text

    @property
    def text(self):
        if self._raise_on_text:
            raise ValueError("blocked by safety filters")
        return self._text


def test_parse_intent_json_handles_plain_json():
    resp = _FakeResponse(text='{"needs_more_info": false, "sql_query": "SELECT 1"}')
    data, raw = chatbot_service.parse_intent_json(resp)
    assert data == {"needs_more_info": False, "sql_query": "SELECT 1"}
    assert raw == resp.text


def test_parse_intent_json_strips_markdown_fences():
    resp = _FakeResponse(text='```json\n{"needs_more_info": false, "sql_query": ""}\n```')
    data, raw = chatbot_service.parse_intent_json(resp)
    assert data == {"needs_more_info": False, "sql_query": ""}


def test_parse_intent_json_extracts_embedded_object():
    resp = _FakeResponse(text='Acá va tu JSON: {"needs_more_info": true, "question": "¿Cuál empresa?"} gracias')
    data, raw = chatbot_service.parse_intent_json(resp)
    assert data == {"needs_more_info": True, "question": "¿Cuál empresa?"}


def test_parse_intent_json_returns_none_for_unparseable_text():
    resp = _FakeResponse(text="esto no es JSON de ninguna forma")
    data, raw = chatbot_service.parse_intent_json(resp)
    assert data is None
    assert raw == "esto no es JSON de ninguna forma"


def test_parse_intent_json_handles_none_response():
    data, raw = chatbot_service.parse_intent_json(None)
    assert data is None
    assert raw is None


# ═══════════════════════════════════════════════════════════════════
# extract_text_from_gemini
# ═══════════════════════════════════════════════════════════════════


def test_extract_text_from_gemini_prefers_direct_text():
    resp = _FakeResponse(text="Hola, soy POLO")
    assert chatbot_service.extract_text_from_gemini(resp) == "Hola, soy POLO"


def test_extract_text_from_gemini_skips_safety_blocked_candidates():
    blocked_candidate = type(
        "C", (), {"finish_reason": "SAFETY", "content": None}
    )()
    ok_part = type("P", (), {"text": "Respuesta válida"})()
    ok_content = type("Content", (), {"parts": [ok_part]})()
    ok_candidate = type("C2", (), {"finish_reason": "STOP", "content": ok_content})()

    resp = _FakeResponse(raise_on_text=True, candidates=[blocked_candidate, ok_candidate])
    assert chatbot_service.extract_text_from_gemini(resp) == "Respuesta válida"


def test_extract_text_from_gemini_returns_none_when_nothing_usable():
    resp = _FakeResponse(raise_on_text=True, candidates=[])
    assert chatbot_service.extract_text_from_gemini(resp) is None


def test_extract_text_from_gemini_handles_none_response():
    assert chatbot_service.extract_text_from_gemini(None) is None


# ═══════════════════════════════════════════════════════════════════
# custom_json_serializer
# ═══════════════════════════════════════════════════════════════════


def test_custom_json_serializer_formats_dates():
    assert chatbot_service.custom_json_serializer(date(2026, 7, 29)) == "2026-07-29"


def test_custom_json_serializer_raises_for_unsupported_types():
    with pytest.raises(TypeError):
        chatbot_service.custom_json_serializer(object())


# ═══════════════════════════════════════════════════════════════════
# get_database_schema: cache en memoria del proceso
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def reset_schema_cache():
    original = chatbot_service._schema_cache
    chatbot_service._schema_cache = None
    yield
    chatbot_service._schema_cache = original


def test_get_database_schema_is_cached_across_calls(reset_schema_cache, monkeypatch):
    from sqlalchemy import create_engine, text as sa_text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    with engine.begin() as conn:
        conn.execute(sa_text("CREATE TABLE empresa (cuil INTEGER PRIMARY KEY, nombre TEXT)"))
    db = SessionLocal()

    call_count = {"n": 0}
    real_inspect = chatbot_service.inspect

    def counting_inspect(bind):
        call_count["n"] += 1
        return real_inspect(bind)

    monkeypatch.setattr(chatbot_service, "inspect", counting_inspect)

    first = chatbot_service.get_database_schema(db)
    second = chatbot_service.get_database_schema(db)

    assert first == second
    assert "empresa" in first
    assert call_count["n"] == 1  # la segunda llamada usó el cache, no volvió a inspeccionar

    third = chatbot_service.get_database_schema(db, force_refresh=True)
    assert call_count["n"] == 2  # force_refresh sí vuelve a inspeccionar
    assert third == first

    db.close()


def test_get_database_schema_excludes_forbidden_tables(reset_schema_cache):
    from sqlalchemy import create_engine, text as sa_text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    with engine.begin() as conn:
        conn.execute(sa_text("CREATE TABLE empresa (cuil INTEGER PRIMARY KEY, nombre TEXT)"))
        conn.execute(sa_text("CREATE TABLE usuario (id_usuario TEXT PRIMARY KEY)"))
    db = SessionLocal()

    schema = chatbot_service.get_database_schema(db)
    assert "empresa" in schema
    assert "'usuario'" not in schema

    db.close()


# ═══════════════════════════════════════════════════════════════════
# _generate: dispatcher resiliente entre modelos candidatos
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def isolated_model_state(monkeypatch):
    """Aísla el estado global de selección de modelo entre tests."""
    monkeypatch.setattr(chatbot_service, "_active_model_index", 0)
    monkeypatch.setattr(chatbot_service, "_model_instances", {})
    yield


def test_generate_falls_back_to_next_candidate_and_sticks(monkeypatch, isolated_model_state):
    calls = []

    class FakeModel:
        def __init__(self, name):
            self.name = name

        def generate_content(self, prompt, generation_config=None):
            calls.append(self.name)
            if self.name == "modelo-roto":
                raise RuntimeError("404 no longer available")
            return _FakeResponse(text="ok")

    monkeypatch.setattr(chatbot_service, "_MODEL_CANDIDATES", ["modelo-roto", "modelo-bueno"])
    monkeypatch.setattr(chatbot_service, "_get_model_instance", lambda name: FakeModel(name))

    resp1 = chatbot_service._generate("prompt", chatbot_service.FINAL_GENERATION_CONFIG)
    assert resp1.text == "ok"
    assert calls == ["modelo-roto", "modelo-bueno"]
    assert chatbot_service._active_model_index == 1

    # Segunda llamada: ya debería ir directo al modelo bueno, sin reintentar el roto.
    calls.clear()
    resp2 = chatbot_service._generate("prompt", chatbot_service.FINAL_GENERATION_CONFIG)
    assert resp2.text == "ok"
    assert calls == ["modelo-bueno"]


def test_generate_raises_when_every_candidate_fails(monkeypatch, isolated_model_state):
    class FailingModel:
        def __init__(self, name):
            self.name = name

        def generate_content(self, prompt, generation_config=None):
            raise RuntimeError(f"{self.name} no disponible")

    monkeypatch.setattr(chatbot_service, "_MODEL_CANDIDATES", ["a", "b"])
    monkeypatch.setattr(chatbot_service, "_get_model_instance", lambda name: FailingModel(name))

    with pytest.raises(RuntimeError):
        chatbot_service._generate("prompt", chatbot_service.FINAL_GENERATION_CONFIG)
