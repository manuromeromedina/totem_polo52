import os

import pytest

try:
    from google.cloud import speech
except ImportError:  # pragma: no cover - librería opcional en CI
    speech = None


GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


@pytest.mark.integration
@pytest.mark.skipif(speech is None, reason="google-cloud-speech no instalado")
@pytest.mark.skipif(not GOOGLE_CREDS, reason="GOOGLE_APPLICATION_CREDENTIALS no configurada")
def test_google_speech_client_initializes():
    """
    Comprueba que las credenciales permiten crear el cliente de Speech-to-Text.
    """
    client = speech.SpeechClient()
    assert client is not None
