# backend/security/authorization.py
from fastapi import Depends, HTTPException, status
from backend.security.authentication import get_current_device, AuthenticatedDevice


class PermissionChecker:
    """Enforces fine-grained permission-based authorizations across API endpoints."""

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, device: AuthenticatedDevice = Depends(get_current_device)) -> AuthenticatedDevice:
        if self.required_permission not in device.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission scope: '{self.required_permission}'."
            )
        return device


# Reusable permission checkpoints
require_chat_permission = PermissionChecker("chat")
require_system_status_permission = PermissionChecker("system_status")
require_safe_commands_permission = PermissionChecker("safe_commands")
