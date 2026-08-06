# app/services/voice_service.py
import os

from fastapi import HTTPException

from app.services.common import GENERIC_ERROR_MESSAGE

try:
    from google.cloud import speech_v1 as speech
    from google.cloud import texttospeech

    google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if google_credentials_path and os.path.exists(google_credentials_path):
        speech_client = speech.SpeechClient()
        tts_client = texttospeech.TextToSpeechClient()
        VOICE_PROVIDER = "google"
        print(" Google Cloud Speech/TTS configurado")
    else:
        speech_client = None
        tts_client = None
        VOICE_PROVIDER = None
        print(" Credenciales de Google Cloud no encontradas")
except ImportError:
    speech = None
    texttospeech = None
    speech_client = None
    tts_client = None
    VOICE_PROVIDER = None
    print(" google-cloud-speech/texttospeech no instalados")


# ═══════════════════════════════════════════════════════════════════
# SPEECH TO TEXT
# ═══════════════════════════════════════════════════════════════════


def transcribe_audio_google(audio_content: bytes, language_code: str = "es-AR") -> str:
    """Convertir audio a texto usando Google Speech-to-Text"""
    try:
        if not speech_client:
            raise HTTPException(status_code=503, detail="Servicio de transcripción no disponible")

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=language_code,
            enable_automatic_punctuation=True,
            model="default",
            use_enhanced=True,
        )

        response = speech_client.recognize(config=config, audio=audio)
        if not response.results:
            return ""

        transcript = " ".join(
            result.alternatives[0].transcript for result in response.results
        ).strip()
        print(f" Transcripción Google: {transcript}")
        return transcript

    except Exception as e:
        print(f" Error en transcripción Google: {str(e)}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)


def transcribe_audio(audio_content: bytes, language_code: str = "es-AR") -> str:
    """Transcribir audio usando Google Cloud"""
    if VOICE_PROVIDER == "google" and speech_client:
        return transcribe_audio_google(audio_content, language_code)

    raise HTTPException(status_code=503, detail=GENERIC_ERROR_MESSAGE)


# ═══════════════════════════════════════════════════════════════════
# TEXT TO SPEECH
# ═══════════════════════════════════════════════════════════════════


def text_to_speech_google(
    text: str, language_code: str = "es-US", voice_name: str = "es-US-Studio-B"
) -> bytes:
    # Google Cloud TTS no ofrece una voz específicamente "es-AR": solo tiene
    # familias es-ES (España) y es-US (español latinoamericano neutro). es-US
    # es la aproximación más cercana disponible al acento argentino.
    # Studio-B: voz de la línea "Studio" de Google (más natural que Neural2,
    # que sonaba robotizada), elegida por el usuario tras comparar muestras.
    # Es una voz masculina (ssml_gender abajo debe coincidir).
    """Convertir texto a voz usando Google Text-to-Speech"""
    try:
        if not tts_client:
            raise HTTPException(status_code=503, detail="Servicio de síntesis de voz no disponible")

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.MALE,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0,
            effects_profile_id=["headphone-class-device"],
        )

        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        print(f" Audio Google generado: {len(response.audio_content)} bytes")
        return response.audio_content

    except Exception as e:
        print(f" Error en síntesis Google: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al generar audio: {str(e)}")


def text_to_speech(text: str, voice_provider: str = None) -> bytes:
    """Sintetizar voz usando Google Cloud (único proveedor soportado)"""
    if voice_provider and voice_provider != "google":
        raise HTTPException(status_code=400, detail="Proveedor de voz no soportado. Usa 'google'.")

    if VOICE_PROVIDER == "google" and tts_client:
        return text_to_speech_google(text)

    raise HTTPException(
        status_code=503,
        detail="No hay servicio de síntesis de voz configurado. Configura GOOGLE_APPLICATION_CREDENTIALS.",
    )


# ═══════════════════════════════════════════════════════════════════
# DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════════════


def get_voice_services_status() -> dict:
    """Obtener estado de los servicios de voz configurados"""
    status = {"provider": VOICE_PROVIDER, "services": {}}

    if speech_client and tts_client:
        status["services"]["google_cloud"] = {
            "speech_to_text": " Disponible",
            "text_to_speech": " Disponible",
        }
    else:
        status["services"]["google_cloud"] = {
            "speech_to_text": " No disponible",
            "text_to_speech": " No disponible",
            "note": "Configura GOOGLE_APPLICATION_CREDENTIALS",
        }

    return status
