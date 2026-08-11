# backend/api/routes/auth.py
import datetime
import uuid
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, status
from pydantic import BaseModel, Field

from backend.database.device_repository import device_repo
from backend.security.token_service import token_service
from backend.security.authentication import get_current_device, AuthenticatedDevice

logger = logging.getLogger("ultron-api")
router = APIRouter()


# ==============================================================================
# SCHEMAS
# ==============================================================================

class PairingSessionResponse(BaseModel):
    success: bool
    session_id: str
    pairing_code: str
    expires_at: str


class PairRequest(BaseModel):
    pairing_code: str = Field(..., min_length=6, max_length=6)
    device_name: str = Field(..., min_length=1, max_length=100)
    device_type: str = Field("android", min_length=1, max_length=30)


class DeviceModel(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    permissions: List[str]
    paired_at: str
    last_seen: str
    revoked: bool


class PairResponse(BaseModel):
    success: bool
    device: DeviceModel
    access_token: str
    token_type: str = "bearer"


# ==============================================================================
# ROUTE ENDPOINTS
# ==============================================================================

@router.post(
    "/auth/pairing-session",
    response_model=PairingSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Pairing Session (Host Loopback-Only)",
    description="Generates a temporary 6-digit secure pairing PIN valid for 180 seconds. Accessible only from localhost."
)
async def create_pairing_session(request: Request) -> PairingSessionResponse:
    # 1. Loopback Protection Guard
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        logger.warning("Blocked remote attempt to generate a pairing session from IP %s", client_host)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Pairing session creation is restricted to local host operations."
        )

    # 2. PIN generation
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    raw_code = token_service.generate_pairing_code()
    code_hash = token_service.hash_string(raw_code)

    now = datetime.datetime.utcnow()
    expires_at = (now + datetime.timedelta(seconds=180)).isoformat() + "Z"

    session_data = {
        "session_id": session_id,
        "code_hash": code_hash,
        "created_at": now.isoformat() + "Z",
        "expires_at": expires_at,
        "used": False
    }

    device_repo.create_pairing_session(session_data)
    logger.info("Pairing session generated successfully. Expires at %s", expires_at)

    return PairingSessionResponse(
        success=True,
        session_id=session_id,
        pairing_code=raw_code,
        expires_at=expires_at
    )


@router.post(
    "/auth/pair",
    response_model=PairResponse,
    status_code=status.HTTP_200_OK,
    summary="Pair Mobile Client Device",
    description="Validate 6-digit temporary PIN code, register client device, and issue a secure hashed Bearer credential."
)
async def pair_device(request: Request, payload: PairRequest) -> PairResponse:
    client_ip = request.client.host if request.client else "unknown"

    # 1. Brute-Force Rate Limiting Lockout Checks
    lockout_status = device_repo.get_lockout_status(client_ip)
    if lockout_status and lockout_status.get("locked_until"):
        locked_until_dt = datetime.datetime.fromisoformat(lockout_status["locked_until"].replace("Z", ""))
        if datetime.datetime.utcnow() < locked_until_dt:
            logger.warning("Blocked pair request from locked out IP: %s", client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Too many pairing attempts. This IP has been locked out for 60 seconds."
            )

    # 2. Hash code and query matching session
    code_hash = token_service.hash_string(payload.pairing_code)
    session = device_repo.get_unused_pairing_session(code_hash)

    # 3. Handle invalid/expired sessions
    if not session:
        device_repo.record_failed_attempt(client_ip)
        logger.warning("Failed pairing attempt from IP: %s (Invalid Code)", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pairing failed. Invalid or already used pairing code."
        )

    # Validate expiration
    expires_dt = datetime.datetime.fromisoformat(session["expires_at"].replace("Z", ""))
    if datetime.datetime.utcnow() > expires_dt:
        device_repo.record_failed_attempt(client_ip)
        device_repo.mark_pairing_session_used(session["session_id"])  # Invalidate expired
        logger.warning("Pairing attempt with expired code from IP: %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pairing failed. Pairing code has expired."
        )

    # 4. Valid PIN code confirmed, perform registration
    device_repo.reset_failed_attempts(client_ip)
    device_repo.mark_pairing_session_used(session["session_id"])

    # Create device records
    device_id = f"{payload.device_type}_{uuid.uuid4().hex[:12]}"
    raw_token = token_service.generate_token()
    token_hash = token_service.hash_string(raw_token)

    now_str = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Standard authorized client scopes as specified: chat, system_status, safe_commands
    standard_permissions = ["chat", "system_status", "safe_commands"]

    device_data = {
        "device_id": device_id,
        "device_name": payload.device_name,
        "device_type": payload.device_type,
        "token_hash": token_hash,
        "permissions": standard_permissions,
        "created_at": now_str,
        "paired_at": now_str,
        "updated_at": now_str,
        "last_seen": now_str,
        "revoked": False
    }

    device_repo.create_device(device_data)
    logger.info("Successfully paired and registered device: %s (%s)", device_id, payload.device_name)

    return PairResponse(
        success=True,
        device=DeviceModel(
            device_id=device_id,
            device_name=payload.device_name,
            device_type=payload.device_type,
            permissions=standard_permissions,
            paired_at=now_str,
            last_seen=now_str,
            revoked=False
        ),
        access_token=raw_token
    )


@router.get(
    "/devices",
    response_model=List[DeviceModel],
    status_code=status.HTTP_200_OK,
    summary="List Registered Devices",
    description="Returns audited registries of all paired client devices. Requires Bearer Authentication."
)
async def list_devices(
    device: AuthenticatedDevice = Depends(get_current_device)
) -> List[DeviceModel]:
    # Audits are limited to authenticated, non-revoked clients
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
    summary="Revoke Device Access",
    description="Instantly revokes access tokens associated with a registered device. Requires Bearer Authentication."
)
async def revoke_device(
    device_id: str,
    device: AuthenticatedDevice = Depends(get_current_device)
):
    logger.info("Revoke device request submitted by: %s (Target: %s)", device.device_id, device_id)
    
    target_device = device_repo.get_device_by_id(device_id)
    if not target_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device matching ID '{device_id}' was not found."
        )

    # Restrict revocation controls to prevent rogue permission escalations
    device_repo.revoke_device(device_id)
    logger.warning("Revoked paired client token successfully: %s", device_id)
    
    return {
        "success": True,
        "message": f"Device matching ID '{device_id}' has been statefully revoked."
    }
