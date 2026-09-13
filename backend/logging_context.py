# backend/logging_context.py — per-request observability context
import uuid
from contextvars import ContextVar

# scoped to the async request lifecycle (FastAPI contextvars propagate)
_REQUEST_ID: ContextVar[str] = ContextVar("ultron_request_id", default="req_unknown")


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def set_request_id(request_id: str) -> str:
    """Binds the current execution context to a request ID. Returns the bound value."""
    resolved = request_id or generate_request_id()
    _REQUEST_ID.set(resolved)
    return resolved


def get_request_id() -> str:
    return _REQUEST_ID.get()