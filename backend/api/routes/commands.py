# backend/api/routes/commands.py
import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from backend.schemas.command import CommandRequest, CommandResponse
from backend.services.command_service import command_service
from backend.security.authorization import require_safe_commands_permission
from backend.security.authentication import AuthenticatedDevice

logger = logging.getLogger("ultron-api")
router = APIRouter()


@router.post(
    "/commands",
    response_model=CommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute System Commands on Host Laptop",
    description="Submits an allowlisted system command to be statefully audited, validated, and executed. Requires Bearer Authentication."
)
async def post_command(
    payload: CommandRequest,
    device: AuthenticatedDevice = Depends(require_safe_commands_permission)
):
    try:
        logger.info("Command '%s' submitted by paired device: %s (%s)", payload.command, device.device_id, device.device_name)
        execution_result = await command_service.execute_command(
            payload.command,
            payload.parameters,
            device.device_id
        )

        # If the service explicitly rejected or failed the command, return mapped HTTP status codes directly as JSONResponses
        if not execution_result.get("success", False):
            err_details = execution_result.get("error", {})
            err_code = err_details.get("code")

            if err_code == "COMMAND_NOT_ALLOWED":
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=execution_result)
            elif err_code in ("HIGH_RISK_COMMAND_REQUIRES_AUTHORIZATION", "DEVICE_REVOKED"):
                return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=execution_result)
            elif err_code == "CONFIRMATION_FAILED":
                return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED, content=execution_result)
            else:
                return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=execution_result)

        return CommandResponse(**execution_result)

    except Exception as e:
        logger.error("Command router transaction exception: %s", e, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "command_id": "cmd_unknown",
                "status": "rejected",
                "error": {
                    "code": "SERVER_TRANSACTION_FAILURE",
                    "message": f"Server failed to complete transaction: {str(e)}"
                }
            }
        )
