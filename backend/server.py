# backend/server.py
import datetime
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging_config import configure_logging
from backend.api.routes.health import router as health_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.system import router as system_router
from backend.api.routes.commands import router as command_router
from backend.api.websocket.connection_manager import manager

# Configure standard structured logging
logger = configure_logging()


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 1. Configure CORS middleware securely
    # Allow comma-separated strings or defaults from config
    cors_origins = settings.cors_origins
    if len(cors_origins) == 1 and cors_origins[0] == "*":
        allow_origins = ["*"]
    else:
        allow_origins = cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True if allow_origins != ["*"] else False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register REST router namespaces under /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")
    app.include_router(command_router, prefix="/api/v1")

    # 3. Base Optional Root Endpoint
    @app.get("/", summary="Root Endpoint")
    async def get_root():
        return {
            "service": "ULTRON-AI",
            "api": "v1"
        }

    # 4. Central Exception Handler to prevent stack trace leakage
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled global API server exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred."
                }
            }
        )

    # 5. Base WebSocket endpoint as defined in ARCHITECTURE.md
    @app.websocket("/ws")
    @app.websocket("/api/v1/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """Stateful WebSocket entrypoint for remote clients."""
        await manager.connect(websocket)
        
        # Connection established handshake packet
        handshake_payload = {
            "event": "CONNECTION_ESTABLISHED",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "message": "Connection to ULTRON-AI gateway established."
        }
        await manager.send_personal_message(handshake_payload, websocket)

        try:
            while True:
                # Keep socket alive and receive JSON payloads
                data = await websocket.receive_json()
                logger.info("Received WebSocket frame payload: %s", data)
                
                # Simple ping-echo handshake response for testing
                if data.get("event") == "PING":
                    await manager.send_personal_message({
                        "event": "PONG",
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                    }, websocket)
                    
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.info("WebSocket client disconnected gracefully.")
        except Exception as e:
            manager.disconnect(websocket)
            logger.error("WebSocket connection disrupted: %s", e)

    return app


# Main application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting ULTRON-AI FastAPI Gateway server...")
    uvicorn.run(
        "backend.server:app",
        host=settings.host,
        port=settings.port,
        reload=True if settings.env == "development" else False
    )
