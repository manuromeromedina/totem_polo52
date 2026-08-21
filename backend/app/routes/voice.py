# app/routes/voice.py

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Body, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import io
import base64
import json

from app.config import get_db
from app.routes.auth import get_current_user
from app.rate_limit import rate_limit
from app import services, models, schemas

MAX_SYNTHESIZE_TEXT_LENGTH = 5000


def _validate_synthesize_text(text: str) -> None:
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")
    if len(text) > MAX_SYNTHESIZE_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"El texto es demasiado largo (máximo {MAX_SYNTHESIZE_TEXT_LENGTH} caracteres)",
        )


# Crear router
router = APIRouter(
    prefix="/api/voice",
    tags=["voice"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)]
)


@router.post("/chat/stream", dependencies=[Depends(rate_limit("voice-chat-stream", max_requests=30, window_seconds=60))])
async def voice_chat_stream(
    payload: Dict = Body(..., description="JSON con 'text' y opcional 'history'"),
    db: Session = Depends(get_db),
):
    """
    Streaming de la respuesta de texto del bot (sin audio).
    Entrega los chunks de texto a medida que se generan.
    """
    text = payload.get("text")
    history = payload.get("history")

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Debes enviar el campo 'text'")

    def stream_generator():
        try:
            for chunk, _, _ in services.get_chat_response_stream(
                db=db, text_message=text, history=history
            ):
                if chunk:
                    yield chunk
        except Exception as exc:
            print(f" Error en streaming de respuesta: {exc}")
            return

    return StreamingResponse(stream_generator(), media_type="text/plain")

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 1: Verificar estado de servicios de voz
# ═══════════════════════════════════════════════════════════════════

@router.get("/status")
async def get_voice_status():
    """
    Verifica qué servicios de voz están disponibles.
    """
    try:
        status = services.get_voice_services_status()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": status,
                "message": "Estado de servicios de voz"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Error al obtener estado de servicios"
            }
        )

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 2: Solo transcribir audio a texto
# ═══════════════════════════════════════════════════════════════════

@router.post("/transcribe", dependencies=[Depends(rate_limit("voice-transcribe", max_requests=20, window_seconds=60))])
async def transcribe_audio_endpoint(
    audio: UploadFile = File(..., description="Archivo de audio (WebM, WAV, MP3)"),
    language: str = "es-AR",
):
    """
    Transcribe audio a texto sin pasar por el chatbot.
    """
    try:
        audio_bytes = await audio.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="El archivo de audio está vacío")

        print(f" Recibido audio: {len(audio_bytes)} bytes, tipo: {audio.content_type}")

        # Bloqueante (llamada de red a Google Speech): sin threadpool, colgaría
        # todo el event loop mientras dura la transcripción.
        transcript = await run_in_threadpool(services.transcribe_audio, audio_bytes, language)

        if not transcript:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "transcript": "",
                    "message": "No se pudo detectar voz en el audio"
                }
            )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "transcript": transcript,
                "length": len(transcript),
                "message": "Audio transcrito exitosamente"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f" Error en transcripción: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al transcribir audio: {str(e)}")

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 3: Solo convertir texto a audio
# ═══════════════════════════════════════════════════════════════════

@router.post("/synthesize", dependencies=[Depends(rate_limit("voice-synthesize", max_requests=20, window_seconds=60))])
async def synthesize_text_endpoint(
    text: str = Body(..., embed=True, description="Texto a convertir en audio")
):
    """
    Convierte texto a voz (streaming MP3) usando Google Cloud.
    """
    try:
        _validate_synthesize_text(text)

        print(f" Sintetizando: {text[:100]}...")

        # Bloqueante (llamada de red a Google TTS): ver nota en /transcribe.
        audio_bytes = await run_in_threadpool(services.text_to_speech, text)

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=response.mp3",
                "Content-Length": str(len(audio_bytes))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f" Error en síntesis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al generar audio: {str(e)}")

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 4: Chat completo con voz (PRINCIPAL)
# ═══════════════════════════════════════════════════════════════════

@router.post("/chat", dependencies=[Depends(rate_limit("voice-chat", max_requests=30, window_seconds=60))])
async def voice_chat_endpoint(
    request: Request,
    audio: Optional[UploadFile] = File(None, description="Archivo de audio del usuario"),
    text: Optional[str] = Form(None, description="Mensaje de texto (alternativa al audio)"),
    history_form: Optional[str] = Form(
        None, description="Historial de conversación en JSON (solo para multipart/form-data)"
    ),
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    - Recibe audio o texto.
    - Transcribe (si hay audio).
    - Procesa con el chatbot (Gemini + DB).
    - Devuelve texto + audio (base64) + resultados de DB.
    """
    try:
        history: Optional[List[Dict]] = None

        # Detectar peticiones JSON puras
        if audio is None and text is None and history_form is None:
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                payload = await request.json()
                text = payload.get("text")
                history = payload.get("history")
                audio_payload = payload.get("audio_base64")
                if audio_payload:
                    audio_bytes = base64.b64decode(audio_payload)
                else:
                    audio_bytes = None
            else:
                audio_bytes = None
        else:
            # Manejar multipart/form-data
            audio_bytes = None
            if history_form:
                try:
                    history = json.loads(history_form)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Historial inválido (JSON esperado)")

        if audio is None and audio_bytes is None and not text:
            raise HTTPException(status_code=400, detail="Debes enviar audio o texto")

        # Si se recibió archivo de audio vía multipart
        if audio and audio_bytes is None:
            file_bytes = await audio.read()
            if len(file_bytes) == 0:
                raise HTTPException(status_code=400, detail="El archivo de audio está vacío")
            print(f"📥 Audio recibido: {len(file_bytes)} bytes")
            audio_bytes = file_bytes

        # Bloqueante (transcripción + Gemini + TTS encadenados): ver nota en /transcribe.
        result = await run_in_threadpool(
            services.get_chat_response_with_audio,
            db,
            audio_bytes,
            text,
            history,
        )

        # Guarda el turno completo (usuario + bot) para que el historial
        # persista entre sesiones (ver GET /history).
        user_turn_text = (text or result.get("transcript") or "").strip()
        bot_turn_text = (result.get("text") or "").strip()
        if user_turn_text:
            db.add(models.ChatMensaje(
                id_usuario=current_user.id_usuario,
                remitente="user",
                contenido=user_turn_text,
            ))
        if bot_turn_text:
            db.add(models.ChatMensaje(
                id_usuario=current_user.id_usuario,
                remitente="bot",
                contenido=bot_turn_text,
            ))
        if user_turn_text or bot_turn_text:
            db.commit()

        payload = {
            "success": True,
            "data": {
                "text": result["text"],
                "audio_base64": result["audio_base64"],
                "transcript": result.get("transcript"),
                "db_results": result.get("db_results", []),
                "corrected_entity": result.get("corrected_entity")
            },
            "error": result.get("error", False),
            "message": "Respuesta generada exitosamente"
        }

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(payload)
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f" Error en chat con voz: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "data": {
                    "text": "No se pudo procesar la consulta en este momento. Intentá nuevamente más tarde.",
                    "audio_base64": "",
                    "transcript": None,
                    "db_results": [],
                    "corrected_entity": None,
                },
                "error": True,
                "message": "El servidor no pudo responder la consulta"
            }
        )

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 4b: Historial de conversación del usuario logueado
# ═══════════════════════════════════════════════════════════════════

@router.get("/history", response_model=List[schemas.ChatMensajeOut], summary="Historial de chat del usuario")
def get_chat_history(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve toda la conversación previa del usuario logueado, en orden cronológico."""
    return (
        db.query(models.ChatMensaje)
        .filter(models.ChatMensaje.id_usuario == current_user.id_usuario)
        .order_by(models.ChatMensaje.fecha.asc(), models.ChatMensaje.id_mensaje.asc())
        .all()
    )

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 5: Test del pipeline completo
# ═══════════════════════════════════════════════════════════════════

@router.get("/test", dependencies=[Depends(rate_limit("voice-test", max_requests=5, window_seconds=60))])
async def test_voice_pipeline_endpoint(
    db: Session = Depends(get_db)
):
    """
    Prueba pipeline:
    - TTS
    - Chat response
    """
    try:
        # Bloqueante (TTS + chat encadenados): ver nota en /transcribe.
        test_results = await run_in_threadpool(services.test_voice_pipeline, db)
        return JSONResponse(
            status_code=200,
            content={
                "success": len(test_results["errors"]) == 0,
                "data": test_results,
                "message": test_results["summary"]
            }
        )

    except Exception as e:
        print(f" Error en test: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error ejecutando tests: {str(e)}")

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 6: Obtener audio de respuesta en base64 (para frontend)
# ═══════════════════════════════════════════════════════════════════

@router.post("/synthesize-base64", dependencies=[Depends(rate_limit("voice-synthesize-base64", max_requests=20, window_seconds=60))])
async def synthesize_text_base64_endpoint(
    text: str = Body(..., embed=True)
):
    """
    Igual que /synthesize pero devuelve el audio en base64 (útil para frontend).
    """
    try:
        _validate_synthesize_text(text)

        # Bloqueante (llamada de red a Google TTS): ver nota en /transcribe.
        audio_bytes = await run_in_threadpool(services.text_to_speech, text)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "audio_base64": audio_base64,
                "text": text,
                "size_bytes": len(audio_bytes),
                "message": "Audio generado exitosamente"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
