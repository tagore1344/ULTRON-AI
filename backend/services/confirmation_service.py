# backend/services/confirmation_service.py
import asyncio
import datetime
import logging
import uuid
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from backend.schemas.event import EventType, EventEnvelope
from backend.api.websocket.connection_manager import manager

logger = logging.getLogger("ultron-api")


class ConfirmationState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ConfirmationService:
    """Manages asynchronous, non-blocking mobile approval requests with strict timeouts."""

    def __init__(self):
        # Maps request_id -> active tracking dictionary:
        # { "command_id": str, "device_id": str, "event": asyncio.Event,
        #   "decision": str, "expires_at": datetime, "command": str, "parameters": dict }
        self.pending_requests: Dict[str, Dict[str, Any]] = {}

    async def create_and_await_confirmation(
        self,
        command_id: str,
        device_id: str,
        command_name: str,
        parameters: Dict[str, Any],
        timeout_seconds: float = 30.0
    ) -> Tuple[bool, str]:
        """Creates a stateful confirmation transaction and blocks asynchronously until approved or expired."""
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        event = asyncio.Event()

        expires_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(seconds=timeout_seconds)

        self.pending_requests[request_id] = {
            "command_id": command_id,
            "device_id": device_id,
            "event": event,
            "decision": None,
            "expires_at": expires_at,
            "command": command_name,
            "parameters": parameters,
            "state": ConfirmationState.PENDING
        }

        # 1. Dispatch CONFIRMATION_REQUEST event frame to paired client WebSockets
        # Safe description hides internal parameter structures (such as process paths)
        human_description = f"Launch {parameters.get('application', command_name)}" if command_name == "launch_application" else f"Run {command_name}"

        request_packet = {
            "event": EventType.CONFIRMATION_REQUEST,
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "request_id": request_id,
            "command_id": command_id,
            "device_id": device_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "data": {
                "command": command_name,
                "description": human_description,
                "expires_in": int(timeout_seconds)
            }
        }

        logger.info("CONFIRMATION_REQUEST generated: %s (expires in %ds)", request_id, int(timeout_seconds))
        await manager.send_to_device(device_id, request_packet)

        # 2. Block asynchronously utilizing asyncio.wait_for (completely non-blocking to other workers)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)

            # Retrieve decision written by WebSocket callback
            req_data = self.pending_requests.get(request_id)
            if not req_data:
                return False, "Request state was aborted."

            decision = req_data["decision"]
            if decision == "approved":
                logger.info("Confirmation transaction approved: %s", request_id)
                self._cleanup_request(request_id)
                return True, "Approved"
            else:
                logger.warning("Confirmation transaction rejected by client: %s", request_id)
                self._cleanup_request(request_id)
                return False, "Rejected"

        except asyncio.TimeoutError:
            logger.warning("Confirmation transaction timed out: %s after %ds", request_id, int(timeout_seconds))

            # Notify client WebSocket of expiration
            expired_packet = {
                "event": EventType.CONFIRMATION_EXPIRED,
                "event_id": f"evt_{uuid.uuid4().hex[:12]}",
                "request_id": request_id,
                "command_id": command_id,
                "device_id": device_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "data": {
                    "message": "Confirmation window has expired."
                }
            }
            await manager.send_to_device(device_id, expired_packet)

            self._cleanup_request(request_id)
            return False, "Expired"

    def submit_decision(
        self,
        request_id: str,
        command_id: str,
        device_id: str,
        decision: str
    ) -> bool:
        """Validates incoming client responses statefully, waking up the pending async execution path on match."""
        req_data = self.pending_requests.get(request_id)

        # 1. Deep Validation Layer
        if not req_data:
            logger.warning("Validation rejected: Unknown request_id: %s", request_id)
            return False

        if req_data["command_id"] != command_id:
            logger.warning("Validation rejected: Command ID mismatch. Expected %s, got %s", req_data["command_id"], command_id)
            return False

        if req_data["device_id"] != device_id:
            logger.warning("Validation rejected: Device ID mismatch. Expected %s, got %s", req_data["device_id"], device_id)
            return False

        if req_data["state"] != ConfirmationState.PENDING:
            logger.warning("Validation rejected: Transaction is no longer pending: %s", request_id)
            return False

        if datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) > req_data["expires_at"]:
            logger.warning("Validation rejected: Transaction expired: %s", request_id)
            req_data["state"] = ConfirmationState.EXPIRED
            req_data["event"].set()
            return False

        if decision not in ("approved", "rejected"):
            logger.warning("Validation rejected: Invalid decision string: %s", decision)
            return False

        # 2. Replay Protection: Single-use write lock
        req_data["decision"] = decision
        req_data["state"] = ConfirmationState.APPROVED if decision == "approved" else ConfirmationState.REJECTED

        # 3. Wake up blocking async coroutine path
        req_data["event"].set()
        return True

    def cancel_pending_device_requests(self, device_id: str):
        """Aborts and cancels all outstanding confirmation queues associated with a client upon disconnect."""
        for req_id, data in list(self.pending_requests.items()):
            if data["device_id"] == device_id and data["state"] == ConfirmationState.PENDING:
                logger.info("Cancelling pending transaction due to connection dropout: %s", req_id)
                data["state"] = ConfirmationState.CANCELLED
                data["decision"] = "rejected"
                data["event"].set()

    def _cleanup_request(self, request_id: str):
        """Remove outstanding queue memory reference safely to prevent leaks."""
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]


# Singleton instance of real-time confirmation manager
confirmation_service = ConfirmationService()
