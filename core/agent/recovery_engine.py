# core/agent/recovery_engine.py
import logging
from core.agent.task_graph import TaskNode, NodeState

logger = logging.getLogger("ultron-api")


class RecoveryEngine:
    """Manages transaction-recovery pipelines, coordinates retries, and triggers replans on node failures."""

    def handle_failure(self, node: TaskNode) -> str:
        """Processes a failed task node statefully; returns the recovery action chosen."""
        logger.warning("RecoveryEngine processing node failure: %s (%s)", node.id, node.label)

        # 1. Coordinate Retries
        if node.retries < node.max_retries:
            node.retries += 1
            node.state = NodeState.READY # Reset back to READY for a retry run
            logger.info("Recovery: Triggering retry %d/%d for node %s", node.retries, node.max_retries, node.id)
            return "RETRY"

        # 2. Re-plan / Fail-closed if max retries exceeded
        node.state = NodeState.FAILED
        logger.error("Recovery: Max retries exceeded. Node %s failed permanently.", node.id)
        return "FAIL"


recovery_engine = RecoveryEngine()
