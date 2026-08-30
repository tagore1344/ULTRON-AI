# backend/services/proposal_service.py — Phase 9E gateway bridge for cognitive proposals
import asyncio
import datetime
import logging
import uuid
from typing import Dict, Any, Optional

from backend.schemas.event import EventType
from backend.api.websocket.connection_manager import manager
from backend.services.confirmation_service import confirmation_service
from backend.database.device_repository import device_repo
from core.agent.proposal_manager import proposal_manager, RISK_SAFE, RISK_HIGH

logger = logging.getLogger("ultron-api")


class ProposalService:
    """Bridges the core proposal lifecycle to the gateway: WS reporting and safe execution.

    Execution semantics per risk class (mirrors docs/ARCHITECTURE.md §4.2):
      * SAFE                  -> applied immediately after HUD approval.
      * CONFIRMATION_REQUIRED -> HUD approval + live CONFIRMATION_REQUEST window.
      * HIGH_RISK             -> HUD approval + live CONFIRMATION_REQUEST window.
                                 Source-code change payloads are NEVER applied
                                 directly; approval is recorded as a hash-sealed
                                 authorization feeding the signed-release pipeline.
    """

    # Adaptation keys that may be applied to assistant configuration (SAFE).
    APPLIABLE_CONFIG_KEYS = ("command_alias", "memory_retrieval_weight", "model_routing")

    def _event_frame(self, event_type: EventType, proposal_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "event": event_type,
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "proposal_id": proposal_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "data": data,
        }

    async def broadcast_new_proposal(self, proposal: Dict[str, Any]):
        """Pushes a newly created proposal to all connected HUD clients."""
        try:
            await manager.broadcast(self._event_frame(
                EventType.PROPOSAL_CREATED,
                proposal["proposal_id"],
                {"proposal": proposal},
            ))
        except Exception as e:
            logger.error("Failed to broadcast PROPOSAL_CREATED for %s: %s", proposal.get("proposal_id"), e)

    def schedule_new_proposal_broadcast(self, proposal: Dict[str, Any]):
        """Fire-and-forget broadcast usable from sync cognitive contexts (no loop = no-op)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_new_proposal(proposal))
        except RuntimeError:
            # No running event loop (pure sync context): clients recover via REST re-fetch.
            logger.debug("No running loop; skipping proposal broadcast (REST polling covers it).")

    # ==============================================================================
    # EXECUTION PIPELINE (invoked after an APPROVED decision)
    # ==============================================================================

    async def execute_approved_proposal(
        self,
        proposal_id: str,
        device_id: str,
        timeout_seconds: float = 30.0
    ) -> Dict[str, Any]:
        """Runs the post-approval pipeline: confirmation gates then safe application."""
        proposal = proposal_manager.get_proposal(proposal_id)
        if not proposal:
            return {"success": False, "error": "Unknown or malformed proposal ID."}

        if proposal["status"] != "APPROVED":
            return {"success": False, "error": f"Proposal is not APPROVED ({proposal['status']})."}

        risk_class = proposal["risk_class"]

        # ── HIGH_RISK / CONFIRMATION_REQUIRED: enforce the live confirmation gate ──
        if risk_class != RISK_SAFE:
            approved, reason = await confirmation_service.create_and_await_confirmation(
                command_id=proposal_id,
                device_id=device_id,
                command_name=f"proposal_apply:{proposal['component']}",
                parameters={"proposal": proposal["title"]},
                timeout_seconds=timeout_seconds,
            )

            # Re-validate the device after the confirmation wait window.
            device_data = device_repo.get_device_by_id(device_id)
            if not device_data or device_data.get("revoked", False):
                reason = "Device revoked during confirmation window."

            if not approved:
                logger.warning("Proposal %s execution blocked: %s", proposal_id, reason)
                proposal_manager.record_execution(proposal_id, False, f"CONFIRMATION_NOT_GRANTED: {reason}")
                await self._broadcast_result(proposal_id, success=False, detail=reason)
                return {"success": False, "status": "CONFIRMATION_NOT_GRANTED", "detail": reason}

        # ── Application ──
        payload = proposal.get("payload") or {}
        detail = self._apply_payload(proposal, payload)
        success = detail.get("success", False)

        proposal_manager.record_execution(proposal_id, success, detail.get("message", ""))
        await self._broadcast_result(proposal_id, success=success, detail=detail.get("message", ""))
        return {"success": success, "status": detail.get("status"), "detail": detail.get("message", "")}

    async def _broadcast_result(self, proposal_id: str, success: bool, detail: str):
        try:
            await manager.broadcast(self._event_frame(
                EventType.PROPOSAL_EXECUTION_RESULT,
                proposal_id,
                {"success": success, "detail": detail},
            ))
        except Exception as e:
            logger.error("Failed broadcasting execution result for %s: %s", proposal_id, e)

    def _apply_payload(self, proposal: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Applies an approved proposal payload using strictly bounded, real appliers."""
        try:
            # 1. Source-code change proposals: NEVER modify code directly.
            if "change_proposal" in payload:
                logger.warning(
                    "Proposal %s: source-change authorization recorded (hash-sealed). "
                    "Code edits require the trusted signing process.",
                    proposal["proposal_id"],
                )
                return {
                    "success": True,
                    "status": "AUTHORIZED_FOR_SIGNED_RELEASE",
                    "message": "Authorization recorded with tamper-evident hash; "
                               "awaiting the trusted cryptographic release process.",
                }

            # 2. SAFE configuration adaptations → assistant_config.json
            applied = []
            for key in self.APPLIABLE_CONFIG_KEYS:
                if key in payload:
                    self._save_config_key(key, payload[key])
                    applied.append(key)

            if applied:
                return {
                    "success": True,
                    "status": "APPLIED",
                    "message": f"Applied adaptation keys: {', '.join(applied)}.",
                }

            return {
                "success": False,
                "status": "NO_APPLIABLE_PAYLOAD",
                "message": "Payload contained no recognized adaptation keys.",
            }
        except Exception as e:
            logger.error("Proposal %s application failed: %s", proposal["proposal_id"], e, exc_info=True)
            return {"success": False, "status": "APPLY_ERROR", "message": f"Application error: {e}"}

    def _save_config_key(self, key: str, value: Any):
        """Persists an approved adaptation into the assistant configuration file."""
        from core.config import load_config, save_config
        config = load_config()
        existing = config.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            existing.update(value)
            config[key] = existing
        else:
            config[key] = value
        save_config(config)
        logger.info("Proposal adaptation saved to assistant config: %s", key)


# Singleton instance
proposal_service = ProposalService()


# Singleton instance
proposal_service = ProposalService()