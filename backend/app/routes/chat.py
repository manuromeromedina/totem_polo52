from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services import get_chat_response
from app.config import get_db
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

@router.post("/")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        response_text, data, corrected_entity = get_chat_response(db, request.message, request.history)

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
        raise HTTPException(status_code=500, detail=f"Error al procesar el mensaje: {str(e)}")
