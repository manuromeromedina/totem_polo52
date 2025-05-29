from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services import get_chat_response
from app.config import get_db  
from sqlalchemy.orm import Session

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        reply = get_chat_response(db, request.message)  
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el mensaje: {str(e)}")