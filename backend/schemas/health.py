# backend/schemas/health.py
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Pydantic schema validating health endpoint response payloads."""

    status: str = Field(..., description="Operational status of the server.")
    service: str = Field(..., description="Name of the API service.")
    version: str = Field(..., description="Current version of the backend.")
