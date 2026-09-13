# backend/api/routes/proposals.py — Phase 9E Cognitive Change-Proposal Gateway
import datetime
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from core.agent.proposal_manager import proposal_manager, VALID_RISK_CLASSES
from backend.schemas.event import EventType
from backend.services.proposal_service import proposal_service
from backend.api.websocket.connection_manager import manager
from backend.security.authorization import (
    require_system_status_permission,
    require_safe_commands_permission,
)
from backend.security.authentication import AuthenticatedDevice

logger = logging.getLogger("ultron-api")
router = APIRouter()


class ProposalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$", description='"approved" or "rejected".')
    note: Optional[str] = Field(None, description="Optional human note recorded in the audit ledger.")
    confirm_timeout_seconds: float = Field(
        30.0,
        ge=0.0,
        le=120.0,
        description="Live confirmation window for CONFIRMATION_REQUIRED / HIGH_RISK proposals.",
    )


class ProposalCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    reason: str = Field(..., max_length=2000)
    component: str = Field(..., max_length=100)
    risk_class: str = Field(..., description="SAFE, CONFIRMATION_REQUIRED or HIGH_RISK.")
    expected_impact: str = Field(..., max_length=2000)
    proposed_action: str = Field(..., max_length=2000)
    payload: Optional[dict] = None
    source_ref: Optional[str] = None
    expiry_seconds: int = Field(86400, ge=60, le=604800)


@router.get(
    "/cognitive/proposals",
    status_code=status.HTTP_200_OK,
    summary="List Cognitive Change-Proposals",
    description="Returns pending change-proposals for HUD review. Requires Bearer Authentication."
)
async def get_proposals(
    resolved: bool = False,
    proposal_status: Optional[str] = None,
    device: AuthenticatedDevice = Depends(require_system_status_permission),
):
    try:
        proposals = proposal_manager.list_proposals(status=proposal_status, include_resolved=resolved)
        return {"success": True, "count": len(proposals), "proposals": proposals}
    except Exception as e:
        logger.error("Proposal listing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not list proposals.")


@router.get(
    "/cognitive/proposals/{proposal_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Details",
    description="Returns the full sanitized detail packet for one proposal. Requires Bearer Authentication."
)
async def get_proposal_detail(
    proposal_id: str,
    device: AuthenticatedDevice = Depends(require_system_status_permission),
):
    proposal = proposal_manager.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found.")
    return {"success": True, "proposal": proposal}


@router.post(
    "/cognitive/proposals",
    status_code=status.HTTP_201_CREATED,
    summary="Create Cognitive Change-Proposal",
    description="Registers a new change-proposal from an authorized cognitive source and broadcasts it to HUD clients."
)
async def create_proposal(
    payload: ProposalCreateRequest,
    device: AuthenticatedDevice = Depends(require_safe_commands_permission),
):
    if payload.risk_class not in VALID_RISK_CLASSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid risk_class.")

    proposal = proposal_manager.create_proposal(
        title=payload.title,
        reason=payload.reason,
        component=payload.component,
        risk_class=payload.risk_class,
        expected_impact=payload.expected_impact,
        proposed_action=payload.proposed_action,
        payload=payload.payload,
        source=f"device:{device.device_id}",
        source_ref=payload.source_ref,
        expiry_seconds=payload.expiry_seconds,
    )
    if not proposal:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Proposal creation failed.")

    await proposal_service.broadcast_new_proposal(proposal)
    logger.info("Proposal %s created by device %s", proposal["proposal_id"], device.device_id)
    return {"success": True, "proposal": proposal}


@router.post(
    "/cognitive/proposals/{proposal_id}/decision",
    status_code=status.HTTP_200_OK,
    summary="Approve or Reject a Proposal",
    description="Applies a human decision. Approved CONFIRMATION_REQUIRED / HIGH_RISK proposals additionally pass "
                "through the existing live confirmation gate before application."
)
async def post_proposal_decision(
    proposal_id: str,
    payload: ProposalDecisionRequest,
    device: AuthenticatedDevice = Depends(require_safe_commands_permission),
):
    ok, message, proposal = proposal_manager.submit_decision(
        proposal_id=proposal_id,
        device_id=device.device_id,
        decision=payload.decision,
        note=payload.note,
    )
    if not ok:
        # Distinguish unknown IDs (404) from state conflicts (409).
        if "Unknown or malformed" in message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)

    # Notify every connected HUD client of the resolution.
    await manager.broadcast({
        "event": EventType.PROPOSAL_RESOLVED,
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "proposal_id": proposal_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "data": {"status": message, "decision": payload.decision, "by": device.device_id},
    })

    # Approved proposals continue into the execution pipeline.
    if payload.decision == "approved":
        result = await proposal_service.execute_approved_proposal(
            proposal_id,
            device.device_id,
            timeout_seconds=payload.confirm_timeout_seconds,
        )
        return {"success": True, "resolution": message, "execution": result}

    return {"success": True, "resolution": message, "execution": None}


@router.post(
    "/cognitive/proposals/{proposal_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a Pending Proposal",
)
async def post_proposal_cancel(
    proposal_id: str,
    device: AuthenticatedDevice = Depends(require_safe_commands_permission),
):
    ok, message = proposal_manager.cancel_proposal(proposal_id, reason=f"Cancelled by device {device.device_id}")
    if not ok:
        if "Unknown or malformed" in message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return {"success": True, "status": message}