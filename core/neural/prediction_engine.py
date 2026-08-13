# core/neural/prediction_engine.py
import logging
from typing import Dict, Any, List

from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralNodeModel, NeuralEdgeModel

logger = logging.getLogger("ultron-api")


class PredictionEngine:
    """Computes ADVISORY forecasts of failure probabilities by tracing the causal graph."""

    def __init__(self):
        pass

    def compute_advisory_failure_risk(self, target_node_id: str) -> float:
        """
        Traces back causal edges to calculate a subjective failure probability (P_fail).
        Advisory only: does not block or delete plan candidates.
        """
        node = neural_memory.get_node(target_node_id)
        if not node:
            return 0.0

        # Base failure risk is inversely proportional to our belief confidence
        p_fail = 1.0 - node.belief_confidence

        # Trace inbound CAUSES edges to accumulate risk
        conn = neural_memory.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT source_id, causal_influence_delta FROM neural_edges
            WHERE target_id = ? AND relationship_type = 'CAUSES'
            """,
            (target_node_id,)
        )
        for row in cursor.fetchall():
            source_id = row["source_id"]
            influence = row["causal_influence_delta"]

            source_node = neural_memory.get_node(source_id)
            if source_node and source_node.operational_state == "FAILED":
                # Upstream failure propagates risk down the causal edge
                p_fail = max(p_fail, abs(influence))

        conn.close()
        logger.info("PredictionEngine: Calculated advisory failure risk for '%s': %.2f", target_node_id, p_fail)
        return round(p_fail, 3)


# Singleton instance
prediction_engine = PredictionEngine()
