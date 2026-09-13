# core/agent/tool_orchestrator.py
import logging
from core.tools.tool_registry import ToolRegistry

logger = logging.getLogger("ultron-api")


class ToolOrchestrator:
    """Secure adapter layer dispatching agent execution requests exclusively to the canonical ToolRegistry."""

    def __init__(self):
        try:
            self.registry = ToolRegistry()
            logger.info("ToolOrchestrator successfully bound to canonical ToolRegistry.")
        except Exception as e:
            logger.critical("Failed to bind ToolOrchestrator to ToolRegistry: %s", e)
            self.registry = None

    async def execute_action(self, intent: str, target: str) -> str:
        """Forward actions securely to the ToolRegistry. No direct shell or subprocess operations."""
        if self.registry is None:
            raise RuntimeError("Canonical ToolRegistry is offline.")

        logger.info("ToolOrchestrator executing: Intent='%s', Target='%s'", intent, target)

        # Enforce clean payload routing to prevent injection attempts
        result = await self.registry.execute({
            "intent": intent,
            "target": target
        })
        return str(result)


tool_orchestrator = ToolOrchestrator()
