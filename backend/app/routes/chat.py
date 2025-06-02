# app/routes/chat.py
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

class ChatResponse(BaseModel):
    reply: str

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        reply = get_chat_response(db, request.message, request.history)
        # Asegurarse de que reply sea una cadena
        if reply is None:
            reply = "No se pudo generar una respuesta."
        elif not isinstance(reply, str):
            reply = str(reply)  # Convertir a cadena si es otro tipo
        print(f"Respuesta enviada al frontend: {reply}")  # Depuración
        return ChatResponse(reply=reply)
    except Exception as e:
        print(f"Error en el backend: {str(e)}")  # Depuración
        raise HTTPException(status_code=500, detail=f"Error al procesar el mensaje: {str(e)}")