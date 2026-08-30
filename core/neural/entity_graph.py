# core/neural/entity_graph.py
import datetime
from typing import Dict, Any, Optional

from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralNodeModel


class EntityGraph:
    """Manages structural operations and checks for physical/software entity nodes in the Neural Graph."""

    def __init__(self):
        pass

    def add_entity(self, entity_id: str, label: str, properties: Dict[str, Any] = None) -> bool:
        """Saves a newly discovered hardware or software Entity node."""
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        node = NeuralNodeModel(
            node_id=entity_id,
            node_type="ENTITY",
            label=label,
            properties=properties or {},
            belief_confidence=0.95, # Initial discovery confidence
            operational_state="KNOWN",
            last_updated=now_str
        )
        # Evaluate standard policy state before saving
        node.operational_state = node.evaluate_operational_state()
        return neural_memory.save_node(node)

    def get_entity(self, entity_id: str) -> Optional[NeuralNodeModel]:
        """Retrieves an Entity node by ID."""
        node = neural_memory.get_node(entity_id)
        if node and node.node_type == "ENTITY":
            return node
        return None


# Singleton instance
entity_graph = EntityGraph()
