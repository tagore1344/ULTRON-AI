# backend/api/websocket/connection_manager.py
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("ultron-api")


class ConnectionManager:
    """Manages active, stateful client WebSocket sessions securely."""

    def __init__(self):
        # Maps active websockets to connection details
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept connection and register websocket session."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established. Active clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove disconnected websocket session."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket connection closed. Active clients: %d", len(self.active_connections))

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a private message to a specific active websocket client."""
        if websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Error sending personal message: %s", e)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast an event to all statefully connected clients."""
        logger.debug("Broadcasting message to %d clients", len(self.active_connections))
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("Broadcast failed for socket client: %s", e)
                # Cleanup dead connection
                self.disconnect(connection)


# Global instance of WebSocket ConnectionManager
manager = ConnectionManager()
