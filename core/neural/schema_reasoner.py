# core/neural/schema_reasoner.py
import datetime
import logging

from core.neural.neural_memory import neural_memory
from core.neural.belief_state import belief_state
from core.neural.causal_graph import causal_graph

logger = logging.getLogger("ultron-api")


class SchemaReasoner:
    """Detects contradictions between beliefs and hard physical facts, overriding subjective scores cleanly."""

    def __init__(self):
        pass

    def verify_and_reconcile(self, node_id: str, observed_success: bool) -> bool:
        """
        Detects contradictions: if |observed - belief| >= 0.60, a contradiction is logged.
        Factual observations override subjective beliefs.
        Propagates failures down the causal graph if a component is confirmed FAILED.
        """
        node = neural_memory.get_node(node_id)
        if not node:
            return False

        observed_value = 1.0 if observed_success else 0.0
        contradiction_delta = abs(observed_value - node.belief_confidence)

        if contradiction_delta >= 0.60:
            logger.warning(
                "Contradiction detected on '%s'! Observed Factual Value: %.1f, Subjective Belief: %.2f. Reconciling...",
                node_id, observed_value, node.belief_confidence
            )

        # Ingest hard factual evidence (override subjective confidence)
        belief_state.ingest_evidence(node_id, observed_success, learning_rate=0.8) # Quick learning rate for correction

        # Refresh state
        updated_node = neural_memory.get_node(node_id)
        if updated_node and updated_node.operational_state == "FAILED":
            # Propagate downstream failures
            causal_graph.propagate_causal_failure(node_id)

        return True


# Singleton instance
schema_reasoner = SchemaReasoner()
