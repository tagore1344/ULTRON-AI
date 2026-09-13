# backend/api/routes/chat.py
import datetime
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, status

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.ultron_service import ultron_service
from backend.security.authorization import require_chat_permission
from backend.security.authentication import AuthenticatedDevice

logger = logging.getLogger("ultron-api")
router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Interact with ULTRON AI Brain",
    description="Sends a text prompt to the ULTRON AI brain orchestrator and returns a structured response. Requires Bearer Authentication."
)
async def post_chat(
    payload: ChatRequest,
    device: AuthenticatedDevice = Depends(require_chat_permission)
) -> ChatResponse:
    conv_id = payload.conversation_id or f"session_{uuid.uuid4().hex[:12]}"

    try:
        # Audit conversation request linked back to device
        logger.info("Chat requested by paired device %s (%s)", device.device_id, device.device_name)
        response_text = ultron_service.ask_brain(payload.message)

        return ChatResponse(
            success=True,
            response=response_text,
            conversation_id=conv_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        )
    except Exception as e:
        logger.error("Chat routing transaction failed: %s", e, exc_info=True)
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
