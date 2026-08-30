# core/neural/belief_state.py
import datetime
import logging

from core.neural.neural_memory import neural_memory

logger = logging.getLogger("ultron-api")


class BeliefState:
    """Updates subjective probability states based on evidence using a clean Bayesian-like update loop."""

    def __init__(self):
        pass

    def ingest_evidence(self, node_id: str, success: bool, learning_rate: float = 0.2):
        """
        Updates node belief confidence (B) using evidence and updates operational states.
        B_new = B_old + lambda * (1.0 - B_old) [on success]
        B_new = B_old - lambda * B_old        [on failure]
        """
        node = neural_memory.get_node(node_id)
        if not node:
            logger.warning("BeliefState: Attempted evidence ingestion on non-existent node '%s'", node_id)
            return

        b_old = node.belief_confidence

        if success:
            # Shift toward 1.0
            b_new = b_old + learning_rate * (1.0 - b_old)
        else:
            # Degrade toward 0.0
            b_new = b_old - learning_rate * b_old

        node.belief_confidence = round(max(0.0, min(1.0, b_new)), 3)
        node.operational_state = node.evaluate_operational_state()
        node.last_updated = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

        neural_memory.save_node(node)
        logger.info("Belief updated for '%s': %.3f -> %.3f (State: %s)", node_id, b_old, node.belief_confidence, node.operational_state)


# Singleton instance
belief_state = BeliefState()
