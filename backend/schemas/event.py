# backend/schemas/event.py
import datetime
import uuid
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Centralized, audited system event classifications for WebSocket communications."""

    CONNECTION_ESTABLISHED = "CONNECTION_ESTABLISHED"
    CONNECTION_CLOSED = "CONNECTION_CLOSED"
    PING = "PING"
    PONG = "PONG"

    COMMAND_RECEIVED = "COMMAND_RECEIVED"
    COMMAND_VALIDATED = "COMMAND_VALIDATED"
    COMMAND_CLASSIFIED = "COMMAND_CLASSIFIED"
    COMMAND_AUTHORIZED = "COMMAND_AUTHORIZED"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    COMMAND_STARTED = "COMMAND_STARTED"
    COMMAND_COMPLETED = "COMMAND_COMPLETED"
    COMMAND_FAILED = "COMMAND_FAILED"

    CONFIRMATION_REQUEST = "CONFIRMATION_REQUEST"
    CONFIRMATION_RESPONSE = "CONFIRMATION_RESPONSE"
    CONFIRMATION_EXPIRED = "CONFIRMATION_EXPIRED"
    CONFIRMATION_CANCELLED = "CONFIRMATION_CANCELLED"

    # Phase 9E: Cognitive change-proposal lifecycle events
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    PROPOSAL_RESOLVED = "PROPOSAL_RESOLVED"
    PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
    PROPOSAL_EXECUTION_RESULT = "PROPOSAL_EXECUTION_RESULT"


class EventEnvelope(BaseModel):
    """Pydantic model validating standard structure envelopes for all outbound WS events."""

    event: EventType = Field(..., description="The type of event.")
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}", description="Unique identifier for the event.")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z", description="ISO 8601 UTC timestamp.")
    device_id: Optional[str] = Field(None, description="The device ID associated with the event.")
    command_id: Optional[str] = Field(None, description="The command ID associated with the transaction.")
    request_id: Optional[str] = Field(None, description="The confirmation request ID if applicable.")
    data: Dict[str, Any] = Field(default_factory=dict, description="Custom event payload data dictionary.")
