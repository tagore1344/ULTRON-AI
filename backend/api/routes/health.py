# backend/api/routes/health.py
from fastapi import APIRouter, status
from backend.config import settings
from backend.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Service Health Status",
    description="Determine if the host's FastAPI gateway is online and serving clients."
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="ultron-api",
        version=settings.app_version
    )
