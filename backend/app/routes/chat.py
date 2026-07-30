#app/routes/chat.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from app.services import get_chat_response, GENERIC_ERROR_MESSAGE
from app.config import get_db
from app.rate_limit import rate_limit
from sqlalchemy.orm import Session
from typing import List, Dict, Optional

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    redirect_slashes=True,
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None

@router.post("/", dependencies=[Depends(rate_limit("chat", max_requests=30, window_seconds=60))])
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # get_chat_response es sincrónico y bloqueante (llamadas a Gemini + queries
        # a la DB). Llamarlo directo desde un endpoint `async def` bloquearía el
        # único event loop del proceso: mientras se procesa un chat, TODO el resto
        # de la API (incluso endpoints livianos como /health) queda colgado.
        # run_in_threadpool lo corre en un hilo aparte para que no bloquee.
        response_text, data, corrected_entity = await run_in_threadpool(
            get_chat_response, db, request.message, request.history
        )

        if not isinstance(response_text, str):
            response_text = str(response_text)

        print(f"Respuesta enviada al frontend: {response_text}")

        return {
            "reply": response_text,
            "data": data,
            "corrected_entity": corrected_entity
        }

    except Exception as e:
        print(f"Error en el backend: {str(e)}")
        raise HTTPException(status_code=500, detail=GENERIC_ERROR_MESSAGE)
