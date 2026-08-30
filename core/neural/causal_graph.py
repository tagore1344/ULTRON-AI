# core/neural/causal_graph.py
import logging
from typing import List, Dict, Any

from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralNodeModel, NeuralEdgeModel

logger = logging.getLogger("ultron-api")


class CausalGraph:
    """Calculates cause-and-effect paths and handles cascading dependency/failure state propagations."""

    def __init__(self):
        pass

    def propagate_causal_failure(self, root_node_id: str) -> List[str]:
        """
        Traverses downstream CAUSES / DEPENDS_ON edges when a root node fails.
        Updates dependent node operational states statefully in SQLite, returning impacted node IDs.
        """
        impacted_nodes = []
        visited = {root_node_id}
        queue = [root_node_id]

        conn = neural_memory.get_connection()
        cursor = conn.cursor()

        while queue:
            curr_id = queue.pop(0)

            # Retrieve all downstream connected nodes via CAUSES relationships
            cursor.execute(
                """
                SELECT target_id, causal_influence_delta FROM neural_edges
                WHERE source_id = ? AND relationship_type = 'CAUSES'
                """,
                (curr_id,)
            )
            for row in cursor.fetchall():
                target_id = row["target_id"]
                influence = row["causal_influence_delta"]

                if target_id not in visited:
                    visited.add(target_id)
                    queue.append(target_id)

                    # Degrade target node confidence based on influence delta
                    target_node = neural_memory.get_node(target_id)
                    if target_node:
                        # Subjective belief degrades statefully
                        target_node.belief_confidence = max(0.0, target_node.belief_confidence - abs(influence))
                        target_node.operational_state = target_node.evaluate_operational_state()
                        neural_memory.save_node(target_node)
                        impacted_nodes.append(target_id)

        conn.close()
        logger.info("Causal propagation completed. Impacted dependent nodes: %s", impacted_nodes)
        return impacted_nodes


# Singleton instance
causal_graph = CausalGraph()
