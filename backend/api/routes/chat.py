# backend/api/routes/chat.py
import datetime
import uuid
import logging
from fastapi import APIRouter, HTTPException, status

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.ultron_service import ultron_service

logger = logging.getLogger("ultron-api")
router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Interact with ULTRON AI Brain",
    description="Sends a text prompt to the ULTRON AI brain orchestrator and returns a structured response."
)
async def post_chat(payload: ChatRequest) -> ChatResponse:
    conv_id = payload.conversation_id or f"session_{uuid.uuid4().hex[:12]}"
    
    try:
        response_text = ultron_service.ask_brain(payload.message)
        
        return ChatResponse(
            success=True,
            response=response_text,
            conversation_id=conv_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        logger.error("Chat routing transaction failed: %s", e, exc_info=True)
        # Raise standard API structured HTTP exception or return standard code
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "ULTRON_CORE_ERROR",
                    "message": "ULTRON could not process the request."
                }
            }
        )
