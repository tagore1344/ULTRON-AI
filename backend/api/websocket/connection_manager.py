# backend/api/websocket/connection_manager.py
import datetime
import uuid
import logging
from typing import Dict, Any, List, Optional
from fastapi import WebSocket, status

from backend.database.device_repository import device_repo
from backend.security.token_service import token_service

logger = logging.getLogger("ultron-api")


class ConnectionManager:
    """Statefully tracks authorized WebSocket client connections and manages private event dispatches."""

    def __init__(self):
        # Maps active session_id -> metadata dictionary:
        # { "device_id": str, "connected_at": str, "last_seen": str, "connection": WebSocket }
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # In-memory secure short-lived, single-use WebSocket tickets:
        # { ticket_hash: { "device_id": str, "expires_at": datetime } }
        self.active_tickets: Dict[str, Dict[str, Any]] = {}

    # ==============================================================================
    # WS TICKET LIFECYCLE
    # ==============================================================================

    def create_ws_ticket(self, device_id: str) -> str:
        """Generate a cryptographically secure, single-use, 15-second WebSocket connection ticket."""
        raw_ticket = token_service.generate_token()
        ticket_hash = token_service.hash_string(raw_ticket)

        expires_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(seconds=15)
        self.active_tickets[ticket_hash] = {
            "device_id": device_id,
            "expires_at": expires_at
        }

        logger.info("Generated 15-second WS ticket for device: %s", device_id)
        return raw_ticket

    def _validate_and_consume_ticket(self, raw_ticket: str) -> Optional[str]:
        """Validate and immediately consume/invalidate the single-use ticket, returning device_id if valid."""
        ticket_hash = token_service.hash_string(raw_ticket)
        if ticket_hash not in self.active_tickets:
            return None

        ticket_data = self.active_tickets.pop(ticket_hash)  # Consume instantly
        expires_at = ticket_data["expires_at"]

        if datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) > expires_at:
            logger.warning("Attempted connect with expired WS ticket.")
            return None

        return ticket_data["device_id"]

    # ==============================================================================
    # SESSION LIFECYCLE
    # ==============================================================================

    async def authenticate_and_connect(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Validate credentials (header or ticket) during handshake, registering device sessions."""
        device_id: Optional[str] = None

        # 1. Attempt standard HTTP Handshake Authorization Header first
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ")[1]
            token_hash = token_service.hash_string(raw_token)
            device_data = device_repo.get_device_by_hash(token_hash)
            if device_data and not device_data.get("revoked", False):
                device_id = device_data["device_id"]

        # 2. Attempt safe, short-lived single-use ticket fallback if headers aren't sent
        if not device_id:
            ticket_param = websocket.query_params.get("ticket")
            if ticket_param:
                device_id = self._validate_and_consume_ticket(ticket_param)

        # 3. Handle auth failure instantly
        if not device_id:
            logger.warning("Unauthenticated WebSocket handshake rejected.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        # Verify device database status one more time to prevent stale access
        device_data = device_repo.get_device_by_id(device_id)
        if not device_data or device_data.get("revoked", False):
            logger.warning("Paired client connection attempt rejected (revoked status check): %s", device_id)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        # 4. Successful handshake, register session
        await websocket.accept()
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

        self.active_sessions[session_id] = {
            "device_id": device_id,
            "connected_at": now_str,
            "last_seen": now_str,
            "connection": websocket
        }

        # Update last seen in SQLite safely
        device_repo.update_last_seen(device_id)
        logger.info("Stateful WS connection established. Session: %s, Device: %s", session_id, device_id)

        return {
            "session_id": session_id,
            "device_id": device_id,
            "connected_at": now_str
        }

    def disconnect(self, websocket: WebSocket) -> Optional[str]:
        """Disconnect and statefully delete active session reference on client dropout."""
        target_session_id = None
        for sess_id, meta in list(self.active_sessions.items()):
            if meta["connection"] == websocket:
                target_session_id = sess_id
                device_id = meta["device_id"]
                del self.active_sessions[sess_id]
                logger.info("WS connection terminated gracefully. Session: %s, Device: %s", sess_id, device_id)
                break
        return target_session_id

    async def evict_device_sessions(self, device_id: str):
        """Immediately disconnect and evict all active sessions mapped to a revoked device."""
        for sess_id, meta in list(self.active_sessions.items()):
            if meta["device_id"] == device_id:
                ws = meta["connection"]
                logger.warning("Evicting active session belonging to revoked device: %s", device_id)
                try:
                    await ws.close(code=status.WS_1008_POLICY_VIOLATION)
                except Exception:
                    pass
                if sess_id in self.active_sessions:
                    del self.active_sessions[sess_id]

    def update_session_heartbeat(self, websocket: WebSocket):
        """Throttle-updates the last seen timestamps on active web sockets."""
        for sess_id, meta in self.active_sessions.items():
            if meta["connection"] == websocket:
                now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
                meta["last_seen"] = now_str
                break

    # ==============================================================================
    # DISPATCH AND BROKER EVENTS
    # ==============================================================================

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a direct JSON message to a specific active WebSocket socket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("Error sending personal message to socket: %s", e)

    async def send_to_device(self, device_id: str, event: Dict[str, Any]):
        """Private event broker: Pushes event only to connections associated with device_id."""
        logger.debug("Routing private event '%s' to device %s", event.get("event"), device_id)
        for meta in list(self.active_sessions.values()):
            if meta["device_id"] == device_id:
                ws = meta["connection"]
                try:
                    await ws.send_json(event)
                except Exception as e:
                    logger.error("Failed to send private event to device %s: %s", device_id, e)

    async def broadcast(self, event: Dict[str, Any]):
        """System-wide notification broker: Pushes event to all connected active clients."""
        logger.debug("Broadcasting event '%s' to all connected clients", event.get("event"))
        for sess_id, meta in list(self.active_sessions.items()):
            ws = meta["connection"]
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.error("Failed to broadcast event to session %s: %s", sess_id, e)


# Global instance of ConnectionManager
manager = ConnectionManager()
