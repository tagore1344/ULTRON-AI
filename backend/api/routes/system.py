# backend/api/routes/system.py
import logging
from fastapi import APIRouter, Depends, status

from backend.schemas.system import SystemStatusResponse
from backend.services.system_service import system_service
from backend.security.authorization import require_system_status_permission
from backend.security.authentication import AuthenticatedDevice

logger = logging.getLogger("ultron-api")
router = APIRouter()


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get System Telemetry Status",
    description="Collects and returns real-time hardware status metrics of the laptop host. Requires Bearer Authentication."
)
async def get_system_status(
    device: AuthenticatedDevice = Depends(require_system_status_permission)
) -> SystemStatusResponse:
    logger.info("Collecting hardware telemetry metrics requested by paired client: %s (%s)", device.device_id, device.device_name)
    telemetry_data = system_service.get_telemetry()
    return SystemStatusResponse(**telemetry_data)
