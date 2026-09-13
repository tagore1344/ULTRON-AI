# core/neural/relation_graph.py
import uuid
from typing import Optional

from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralEdgeModel


class RelationGraph:
    """Manages structural and associative relationships (edges) between nodes in the Neural Graph."""

    def __init__(self):
        pass

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        link_confidence: float = 1.0,
        causal_influence_delta: float = 0.0
    ) -> bool:
        """Saves a directed connection between two existing Neural Nodes."""
        edge_id = f"edge_{uuid.uuid4().hex[:12]}"
        edge = NeuralEdgeModel(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            link_confidence=link_confidence,
            causal_influence_delta=causal_influence_delta
        )
        return neural_memory.save_edge(edge)

    def get_relation(self, source_id: str, target_id: str, relationship_type: str) -> Optional[NeuralEdgeModel]:
        """Queries an edge connection by source, target, and relationship type."""
        conn = neural_memory.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT edge_id FROM neural_edges
            WHERE source_id = ? AND target_id = ? AND relationship_type = ?
            """,
            (source_id, target_id, relationship_type)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return neural_memory.get_edge(row["edge_id"])
        return None


# Singleton instance
relation_graph = RelationGraph()
