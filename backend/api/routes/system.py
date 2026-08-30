# backend/api/routes/system.py
import logging
from fastapi import APIRouter, Depends, status

from backend.schemas.system import SystemStatusResponse
from backend.services.system_service import system_service
from core.update.version_manager import version_manager
from core.update.update_manager import update_manager
from backend.security.authorization import require_system_status_permission
from backend.security.authentication import get_current_device, AuthenticatedDevice

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


@router.get(
    "/system/version",
    status_code=status.HTTP_200_OK,
    summary="Get Authoritative System Build Versions",
    description="Returns public build and mobile compatibility version mappings."
)
async def get_system_version():
    logger.info("Version metadata queried successfully.")
    return {
        "application_version": version_manager.active_identity["application_version"],
        "backend_version": version_manager.active_identity["application_version"],
        "mobile_compat_version": "1.0.0",
        "database_schema_version": 2
    }


@router.get(
    "/system/update/status",
    status_code=status.HTTP_200_OK,
    summary="Get Autonomous Self-Update Subsystem Status",
    description="Returns active upgrade state, current release metadata, and historical records. Requires Bearer Authentication."
)
async def get_update_status(
    device: AuthenticatedDevice = Depends(get_current_device)
):
    logger.info("Update subsystem status logs queried by paired device %s (%s)", device.device_id, device.device_name)
    return update_manager.get_status()
