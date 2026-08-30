# backend/security/authentication.py
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from backend.database.device_repository import device_repo
from backend.security.token_service import token_service

logger = logging.getLogger("ultron-api")
security_scheme = HTTPBearer(auto_error=True)


class AuthenticatedDevice(BaseModel):
    """Pydantic model containing trusted, validated device transaction contexts."""

    device_id: str = Field(..., description="Unique client registration identifier.")
    device_name: str = Field(..., description="Name of the paired user phone.")
    device_type: str = Field(..., description="Type of hardware device (e.g. android).")
    permissions: list = Field(..., description="Allocated command capabilities.")
    revoked: bool = Field(..., description="Has this device been revoked?")


async def get_current_device(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> AuthenticatedDevice:
    """FastAPI security dependency validating incoming HTTP Bearer credentials."""
    raw_token = credentials.credentials
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is missing or malformed."
        )

    # 1. Secure Hashing Comparison
    token_hash = token_service.hash_string(raw_token)
    device_data = device_repo.get_device_by_hash(token_hash)

    # 2. Validation Checks
    if not device_data:
        logger.warning("Unrecognized or spoofed Bearer token attempt received.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied. Invalid credentials."
        )

    if device_data.get("revoked", False):
        logger.warning("Revoked paired client connection attempt: %s", device_data["device_id"])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied. Paired device has been revoked."
        )

    # 3. Update Last-Seen telemetry timestamp statefully
    device_repo.update_last_seen(device_data["device_id"])

    # Return context safely mapping Pydantic keys
    return AuthenticatedDevice(
        device_id=device_data["device_id"],
        device_name=device_data["device_name"],
        device_type=device_data["device_type"],
        permissions=device_data["permissions"],
        revoked=device_data["revoked"]
    )
