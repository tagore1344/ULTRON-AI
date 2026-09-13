# backend/api/routes/context.py
import logging
from fastapi import APIRouter, HTTPException, Depends, status

from core.context.self_model import self_model
from core.context.world_model import world_model
from core.context.long_term_goals import goal_manager_9b
from core.context.memory_manager import memory_manager
from backend.security.authorization import require_system_status_permission, require_safe_commands_permission
from backend.security.authentication import AuthenticatedDevice

logger = logging.getLogger("ultron-api")
router = APIRouter()


@router.get(
    "/context/self-model",
    status_code=status.HTTP_200_OK,
    summary="Get ULTRON Self Model",
    description="Returns the sanitized real-time state, capabilities, and resource telemetry of the agent. Requires Bearer Authentication."
)
async def get_self_model(
    device: AuthenticatedDevice = Depends(require_system_status_permission)
):
    try:
        logger.info("Self-model queried by device %s (%s)", device.device_id, device.device_name)
        return {
            "success": True,
            "data": self_model.get_summary()
        }
    except Exception as e:
        logger.error("Failed to fetch self-model snapshot: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve self-model snapshot."
        )


@router.get(
    "/context/world-model",
    status_code=status.HTTP_200_OK,
    summary="Get ULTRON World Model",
    description="Returns the real-time scanned external environment context. Requires Bearer Authentication."
)
async def get_world_model(
    device: AuthenticatedDevice = Depends(require_system_status_permission)
):
    try:
        logger.info("World-model queried by device %s (%s)", device.device_id, device.device_name)
        return {
            "success": True,
            "data": world_model.get_summary()
        }
    except Exception as e:
        logger.error("Failed to fetch world-model summary: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve world-model snapshot."
        )


@router.get(
    "/context/goals/active",
    status_code=status.HTTP_200_OK,
    summary="Get Active Long-Term Goals",
    description="Lists active long-term goals and subgoals. Requires Bearer Authentication."
)
async def get_active_goals(
    device: AuthenticatedDevice = Depends(require_system_status_permission)
):
    try:
        logger.info("Active goals list queried by device %s (%s)", device.device_id, device.device_name)
        return {
            "success": True,
            "data": goal_manager_9b.get_active_goals_with_subgoals()
        }
    except Exception as e:
        logger.error("Failed to fetch active long-term goals: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goals ledger."
        )


@router.post(
    "/context/memory/clear",
    status_code=status.HTTP_200_OK,
    summary="Reset All Memory Context",
    description="Clears episodic, semantic, strategy, and working memories cleanly. Requires Bearer Authentication with safe commands permissions."
)
async def post_clear_memory(
    device: AuthenticatedDevice = Depends(require_safe_commands_permission)
):
    try:
        logger.warning("All contextual memory pools manual reset requested by authorized device %s (%s)", device.device_id, device.device_name)
        memory_manager.clear_all_context_memory()
        return {
            "success": True,
            "message": "All contextual memory pools successfully cleared."
        }
    except Exception as e:
        logger.error("Contextual reset sequence failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear contextual memory."
        )
