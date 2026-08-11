# backend/api/routes/system.py
import logging
from fastapi import APIRouter, status

from backend.schemas.system import SystemStatusResponse
from backend.services.system_service import system_service

logger = logging.getLogger("ultron-api")
router = APIRouter()


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get System Telemetry Status",
    description="Collects and returns real-time hardware status metrics of the laptop host."
)
async def get_system_status() -> SystemStatusResponse:
    logger.info("Collecting hardware telemetry metrics...")
    telemetry_data = system_service.get_telemetry()
    return SystemStatusResponse(**telemetry_data)
