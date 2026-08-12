# backend/server.py
import datetime
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging_config import configure_logging
from backend.database.connection import initialize_database
from backend.api.routes.health import router as health_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.system import router as system_router
from backend.api.routes.commands import router as command_router
from backend.api.routes.auth import router as auth_router
from backend.api.websocket.connection_manager import manager
from backend.services.confirmation_service import confirmation_service

# Configure standard structured logging
logger = configure_logging()


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    # 1. Initialize SQLite database, directory buffers, and default schemas statefully
    initialize_database()

    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 2. Configure CORS middleware securely
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

    # 3. Register REST router namespaces under /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")
    app.include_router(command_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")

    # 4. Base Optional Root Endpoint
    @app.get("/", summary="Root Endpoint")
    async def get_root():
        return {
            "service": "ULTRON-AI",
            "api": "v1"
        }

    # 5. Central Exception Handler to prevent stack trace leakage
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

    # 6. Secure Authenticated WebSocket endpoint as defined in ARCHITECTURE.md
    @app.websocket("/ws")
    @app.websocket("/api/v1/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """Stateful secure WebSocket entrypoint for authorized remote clients."""
        # 1. Authenticate during handshake (uses Bearer headers or short-lived Tickets)
        meta = await manager.authenticate_and_connect(websocket)
        if not meta:
            return  # Handshake rejected/closed statefully

        session_id = meta["session_id"]
        device_id = meta["device_id"]

        # 2. Connection established handshake confirmation packet
        handshake_payload = {
            "event": "CONNECTION_ESTABLISHED",
            "session_id": session_id,
            "device_id": device_id,
            "timestamp": meta["connected_at"],
            "server_version": settings.app_version,
            "message": "Connection to ULTRON-AI gateway established."
        }
        await manager.send_personal_message(handshake_payload, websocket)

        try:
            while True:
                # Keep socket alive and receive JSON payloads
                data = await websocket.receive_json()
                logger.info("Received WebSocket frame payload from %s: %s", device_id, data)

                event_type = data.get("event")

                # 3. Heartbeat PING-PONG handler
                if event_type == "PING":
                    manager.update_session_heartbeat(websocket)
                    await manager.send_personal_message({
                        "event": "PONG",
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
                    }, websocket)

                # 4. Interactive Confirmation Response handler
                elif event_type == "CONFIRMATION_RESPONSE":
                    manager.update_session_heartbeat(websocket)
                    req_id = data.get("request_id")
                    cmd_id = data.get("command_id")
                    decision = data.get("decision")

                    # Submit decision securely to unlock the pending execution path
                    success = confirmation_service.submit_decision(
                        request_id=req_id,
                        command_id=cmd_id,
                        device_id=device_id,
                        decision=decision
                    )

                    if success:
                        logger.info("Decision '%s' accepted for request %s", decision, req_id)
                    else:
                        logger.warning("Rejected invalid confirmation response packet for request %s", req_id)

        except WebSocketDisconnect:
            manager.disconnect(websocket)
            confirmation_service.cancel_pending_device_requests(device_id)
            logger.info("WebSocket client disconnected gracefully.")
        except Exception as e:
            manager.disconnect(websocket)
            confirmation_service.cancel_pending_device_requests(device_id)
            logger.error("WebSocket connection disrupted statefully: %s", e)

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
