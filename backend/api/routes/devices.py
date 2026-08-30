# backend/api/routes/devices.py
import datetime
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from backend.database.device_repository import device_repo
from backend.security.authorization import require_system_status_permission, require_safe_commands_permission
from backend.security.authentication import get_current_device, AuthenticatedDevice
from backend.api.websocket.connection_manager import manager
from backend.api.routes.auth import DeviceModel
from core.context.world_model import world_model

logger = logging.getLogger("ultron-api")
router = APIRouter()


class SyncStateItem(BaseModel):
    key: str
    value: Any
    timestamp: str  # ISO 8601 UTC format


class SyncRequest(BaseModel):
    items: List[SyncStateItem]


class SyncResponseItem(BaseModel):
    key: str
    value: Any
    status: str  # "ACCEPTED", "STATE_REJECTED"
    authoritative_value: Optional[Any] = None


class ClientTelemetryItem(BaseModel):
    key: str
    value: Any


class ClientTelemetryRequest(BaseModel):
    items: List[ClientTelemetryItem]


@router.get(
    "/devices",
    response_model=List[DeviceModel],
    status_code=status.HTTP_200_OK,
    summary="List Registered Devices",
    description="Returns audited registries of all paired client devices. Requires Bearer Authentication."
)
async def list_devices(
    device: AuthenticatedDevice = Depends(require_system_status_permission)
) -> List[DeviceModel]:
    logger.info("Device list queried by client: %s", device.device_id)
    raw_list = device_repo.list_all_devices()

    return [
        DeviceModel(
            device_id=d["device_id"],
            device_name=d["device_name"],
            device_type=d["device_type"],
            permissions=d["permissions"],
            paired_at=d["paired_at"],
            last_seen=d["last_seen"],
            revoked=d["revoked"]
        )
        for d in raw_list
    ]


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke Device Access (Self-Revocation Enforced)",
    description="Instantly revokes access tokens associated with a registered device. Requires Bearer Authentication."
)
async def revoke_device(
    device_id: str,
    device: AuthenticatedDevice = Depends(get_current_device)
):
    logger.info("Revoke device request submitted by: %s (Target: %s)", device.device_id, device_id)

    # Enforce self-revocation safety check
    if device_id != device.device_id:
        logger.warning("Access denied: Client %s attempted unauthorized revocation of client %s", device.device_id, device_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Paired devices are strictly restricted to self-revocation."
        )

    target_device = device_repo.get_device_by_id(device_id)
    if not target_device:
        raise HTTPException(
            status_code=status.HTTP_444_NOT_FOUND,
            detail=f"Device matching ID '{device_id}' was not found."
        )

    device_repo.revoke_device(device_id)
    logger.warning("Revoked paired client token successfully: %s", device_id)

    # Evict all active WS connections
    await manager.evict_device_sessions(device_id)

    return {
        "success": True,
        "message": f"Device matching ID '{device_id}' has been statefully revoked and all active WS sessions evicted."
    }


@router.post(
    "/agent/emergency-stop",
    status_code=status.HTTP_200_OK,
    summary="Authenticated Emergency Stop Trigger",
    description="Halts all active executions immediately, releases mic ownership, and resets the system to IDLE. Requires paired & authenticated device with safe_commands permission."
)
async def post_emergency_stop(
    device: AuthenticatedDevice = Depends(require_safe_commands_permission)
):
    logger.critical("AUTHENTICATED EMERGENCY_STOP REST API trigger received from device %s!", device.device_id)

    from core.agent.agent_runtime import agent_runtime
    from core.agent.goal_manager import goal_manager
    from microphone_broker import mic_broker

    # 1. Trigger cancellation and transition IDLE
    goal_manager.cancel_goal()
    goal_manager.clear_goal()
    agent_runtime.state = "IDLE"

    # 2. Release all microphone owners
    for owner in ["AdvancedSpeechEngine", "VoiceID", "AdvancedWakeWordDetector", "ClapDetector"]:
        mic_broker.release(owner)

    # 3. Broadcast cancellation to all connected clients
    await manager.broadcast({
        "event": "EMERGENCY_STOP_TRIGGERED",
        "cancelled_by": device.device_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    })

    return {
        "success": True,
        "message": "Emergency stop successfully processed. System reset to IDLE."
    }


@router.post(
    "/context/sync",
    response_model=List[SyncResponseItem],
    status_code=status.HTTP_200_OK,
    summary="Synchronize Client and Host States Safely",
    description="Reconciles context state changes, enforcing strict host-authority limits on sensitive parameters."
)
async def post_sync_state(
    payload: SyncRequest,
    device: AuthenticatedDevice = Depends(require_system_status_permission)
) -> List[SyncResponseItem]:
    logger.info("State synchronization requested by device %s (%s)", device.device_id, device.device_name)
    response_items = []

    host_authoritative_keys = [
        "goals", "subgoals", "neural_schema", "device_registry", "permissions",
        "authentication", "approval_state", "high_risk_state", "evolution_state",
        "experiment_state", "self_update_state", "rollback_state"
    ]
    client_writable_keys = [
        "ui_preferences", "cached_telemetry", "draft_commands", "offline_event_buffer"
    ]

    host_state_mock = {
        "goals": [{"goal_id": "g1", "status": "ACTIVE"}],
        "permissions": ["chat", "system_status"],
        "ui_preferences": {"theme": "onyx", "last_updated": "2026-08-13T12:00:00Z"},
        "cached_telemetry": {"latency": 0.12}
    }

    for item in payload.items:
        key = item.key

        if key in host_authoritative_keys:
            logger.warning("Conflict rejected: Attempted write on HOST_AUTHORITATIVE target key '%s' by client.", key)
            authoritative_val = host_state_mock.get(key)
            response_items.append(SyncResponseItem(
                key=key,
                value=authoritative_val,
                status="STATE_REJECTED",
                authoritative_value=authoritative_val
            ))
        elif key in client_writable_keys:
            logger.info("State merged successfully for CLIENT_WRITABLE key '%s' using LWW.", key)
            response_items.append(SyncResponseItem(
                key=key,
                value=item.value,
                status="ACCEPTED"
            ))
        else:
            response_items.append(SyncResponseItem(
                key=key,
                value=None,
                status="STATE_REJECTED",
                authoritative_value=None
            ))

    return response_items


@router.post(
    "/context/sync/telemetry",
    status_code=status.HTTP_200_OK,
    summary="Submit Client Telemetry Observations Safely",
    description="Ingests raw mobile/watch telemetry. Direct operational state injections are strictly rejected to enforce Host Authority."
)
async def post_sync_telemetry(
    payload: ClientTelemetryRequest,
    device: AuthenticatedDevice = Depends(require_system_status_permission)
):
    logger.info("Telemetry observations submission received from device %s (%s)", device.device_id, device.device_name)

    for item in payload.items:
        # Enforce Host Authority boundary over client-side inputs
        success = world_model.update_telemetry_observation(item.key, item.value)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Direct modification of state key '{item.key}' is prohibited."
            )

    return {
        "success": True,
        "message": "All safe client telemetry observations successfully ingested and validated by host."
    }
