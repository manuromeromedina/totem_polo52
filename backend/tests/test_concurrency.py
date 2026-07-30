"""
Guardas de regresión para el bug de concurrencia encontrado en producción:
/chat/ y varios endpoints de /api/voice/* eran `async def` pero llamaban
directo a funciones sincrónicas y bloqueantes (Gemini, Google Speech/TTS,
DB), lo que colgaba el único event loop del proceso durante todo el
tiempo de esa llamada -- cualquier otra request (incluso a endpoints
livianos) quedaba esperando.

Estos tests miden tiempo real: si alguien vuelve a llamar a una función
bloqueante sin `run_in_threadpool`, el tiempo total vuelve a ser ~N veces
el de una sola llamada en vez de solaparse, y el test falla.
"""
import asyncio
import time
from unittest.mock import patch

import httpx
import pytest

from app.main import app
from app.rate_limit import reset_rate_limits
from app.routes.auth import require_public_role


class _DummyPublicUser:
    def __init__(self):
        self.id_usuario = 1
        self.roles = [{"tipo_rol": "publico"}]


SIMULATED_BLOCKING_SECONDS = 0.5
CONCURRENT_REQUESTS = 3
# Si las requests se solaparan perfectamente tardarían ~0.5s; si se
# serializaran tardarían ~1.5s. El corte a la mitad separa ambos casos con
# margen para jitter del entorno de test.
SERIALIZED_THRESHOLD = SIMULATED_BLOCKING_SECONDS * CONCURRENT_REQUESTS * 0.6


@pytest.fixture(autouse=True)
def _isolate():
    reset_rate_limits()
    yield
    app.dependency_overrides.pop(require_public_role, None)
    reset_rate_limits()


async def _fire_concurrent_requests(path: str, json_body: dict, count: int = CONCURRENT_REQUESTS) -> float:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        start = time.perf_counter()
        responses = await asyncio.gather(*[client.post(path, json=json_body) for _ in range(count)])
        elapsed = time.perf_counter() - start
        assert all(r.status_code == 200 for r in responses), [r.status_code for r in responses]
        return elapsed


def test_chat_endpoint_does_not_block_the_event_loop():
    def slow_get_chat_response(db, message, history=None):
        time.sleep(SIMULATED_BLOCKING_SECONDS)
        return ("ok", [], None)

    with patch("app.routes.chat.get_chat_response", side_effect=slow_get_chat_response):
        elapsed = asyncio.run(_fire_concurrent_requests("/chat/", {"message": "hola"}))

    assert elapsed < SERIALIZED_THRESHOLD, (
        f"{CONCURRENT_REQUESTS} requests a /chat/ tardaron {elapsed:.2f}s: parecen estar "
        "serializándose (bloqueando el event loop) en vez de solaparse."
    )


def test_voice_transcribe_does_not_block_the_event_loop():
    app.dependency_overrides[require_public_role] = lambda: _DummyPublicUser()

    def slow_transcribe(audio_bytes, language):
        time.sleep(SIMULATED_BLOCKING_SECONDS)
        return "transcripcion simulada"

    with patch("app.routes.voice.services.transcribe_audio", side_effect=slow_transcribe):

        async def _run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                start = time.perf_counter()
                responses = await asyncio.gather(*[
                    client.post(
                        "/api/voice/transcribe",
                        files={"audio": ("a.wav", b"123", "audio/wav")},
                    )
                    for _ in range(CONCURRENT_REQUESTS)
                ])
                elapsed = time.perf_counter() - start
                assert all(r.status_code == 200 for r in responses)
                return elapsed

        elapsed = asyncio.run(_run())

    assert elapsed < SERIALIZED_THRESHOLD, (
        f"{CONCURRENT_REQUESTS} requests a /api/voice/transcribe tardaron {elapsed:.2f}s: "
        "parecen estar serializándose en vez de solaparse."
    )
