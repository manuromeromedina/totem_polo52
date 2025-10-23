# app/routers/voice.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import io
import base64

from app.config import get_db
from app.routes.auth import require_public_role
from app import services

# -------------------------------------------------------------------
# STREAMING (Opcional)
# -------------------------------------------------------------------
# Si se habilita transmisión en vivo, se puede reutilizar la lógica
# de FastAPI WebSocket. Referencia orientativa (comentada):
#
# from fastapi import WebSocket, WebSocketDisconnect
# from google.cloud.speech_v1 import StreamingRecognizeResponse
# 
# @router.websocket("/ws/voice/stream")
# async def voice_stream(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         await websocket.send_text("🚀 Streaming listo. Envía fragmentos de audio base64.")
#         # Aquí se recibirían frames binarios/base64:
#         # while True:
#         #     payload = await websocket.receive_bytes()
#         #     # Procesar frame y emitir resultados parciales:
#         #     await websocket.send_json({"partial": "texto..."})
#     except WebSocketDisconnect:
#         print("Cliente desconectado del streaming de voz.")


# Crear router
router = APIRouter(
    prefix="/api/voice",
    tags=["voice"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_public_role)]
)

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

@router.post("/transcribe")
async def transcribe_audio_endpoint(
    audio: UploadFile = File(..., description="Archivo de audio (WebM, WAV, MP3)"),
    language: str = "es-ES",
):
    """
    Transcribe audio a texto sin pasar por el chatbot.
    """
    try:
        audio_bytes = await audio.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="El archivo de audio está vacío")

        print(f" Recibido audio: {len(audio_bytes)} bytes, tipo: {audio.content_type}")

        transcript = services.transcribe_audio(audio_bytes, language)

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

@router.post("/synthesize")
async def synthesize_text_endpoint(
    text: str = Body(..., embed=True, description="Texto a convertir en audio")
):
    """
    Convierte texto a voz (streaming MP3) usando Google Cloud.
    """
    try:
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="El texto no puede estar vacío")

        if len(text) > 5000:
            raise HTTPException(status_code=400, detail="El texto es demasiado largo (máximo 5000 caracteres)")

        print(f" Sintetizando: {text[:100]}...")

        audio_bytes = services.text_to_speech(text)

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

@router.post("/chat")
async def voice_chat_endpoint(
    audio: Optional[UploadFile] = File(None, description="Archivo de audio del usuario"),
    text: Optional[str] = Body(None, embed=True, description="Mensaje de texto (alternativa al audio)"),
    history: Optional[List[Dict]] = Body(None, embed=True, description="Historial de conversación"),
    db: Session = Depends(get_db)
):
    """
    - Recibe audio o texto.
    - Transcribe (si hay audio).
    - Procesa con el chatbot (Gemini + DB).
    - Devuelve texto + audio (base64) + resultados de DB.
    """
    try:
        if not audio and not text:
            raise HTTPException(status_code=400, detail="Debes enviar audio o texto")

        audio_bytes = None
        if audio:
            audio_bytes = await audio.read()
            if len(audio_bytes) == 0:
                raise HTTPException(status_code=400, detail="El archivo de audio está vacío")
            print(f"📥 Audio recibido: {len(audio_bytes)} bytes")

        result = services.get_chat_response_with_audio(
            db=db,
            audio_content=audio_bytes,
            text_message=text,
            history=history
        )

        return JSONResponse(
            status_code=200,
            content={
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
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f" Error en chat con voz: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando mensaje: {str(e)}")

# ═══════════════════════════════════════════════════════════════════
# ENDPOINT 5: Test del pipeline completo
# ═══════════════════════════════════════════════════════════════════

@router.get("/test")
async def test_voice_pipeline_endpoint(
    db: Session = Depends(get_db)
):
    """
    Prueba pipeline:
    - TTS
    - Chat response
    """
    try:
        test_results = services.test_voice_pipeline(db)
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

@router.post("/synthesize-base64")
async def synthesize_text_base64_endpoint(
    text: str = Body(..., embed=True)
):
    """
    Igual que /synthesize pero devuelve el audio en base64 (útil para frontend).
    """
    try:
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Texto vacío")

        audio_bytes = services.text_to_speech(text)
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# -------------------------------------------------------------------
# STREAMING RESPUESTA (Opcional)
# -------------------------------------------------------------------
# Para enviar el audio de respuesta mientras se genera, se puede
# construir un endpoint alternativo que utilice StreamingResponse con
# un generador que entregue los fragmentos producidos en
# services.chunk_audio_payload. Ejemplo comentado:
#
# @router.post("/synthesize/stream")
# async def synthesize_text_streaming_endpoint(
#     text: str = Body(..., embed=True, description="Texto a convertir")
# ):
#     if not text.strip():
#         raise HTTPException(status_code=400, detail="Texto vacío")
# 
#     audio_bytes = services.text_to_speech(text)
# 
#     def audio_generator():
#         for chunk in services.chunk_audio_payload(audio_bytes):
#             yield chunk
# 
#     return StreamingResponse(
#         audio_generator(),
#         media_type="audio/mpeg"
#     )
