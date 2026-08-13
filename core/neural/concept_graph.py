# core/neural/concept_graph.py
import datetime
from typing import Dict, Any, Optional

from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralNodeModel


class ConceptGraph:
    """Manages high-level abstract conceptual nodes in the Neural Graph."""

    def __init__(self):
        pass

    def add_concept(self, concept_id: str, label: str, properties: Dict[str, Any] = None) -> bool:
        """Saves a high-level Concept node."""
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        node = NeuralNodeModel(
            node_id=concept_id,
            node_type="CONCEPT",
            label=label,
            properties=properties or {},
            belief_confidence=0.5, # Conceptual nodes start with neutral subjective probability B
            operational_state="UNVERIFIED",
            last_updated=now_str
        )
        node.operational_state = node.evaluate_operational_state()
        return neural_memory.save_node(node)

    def get_concept(self, concept_id: str) -> Optional[NeuralNodeModel]:
        """Retrieves a Concept node by ID."""
        node = neural_memory.get_node(concept_id)
        if node and node.node_type == "CONCEPT":
            return node
        return None


# Singleton instance
concept_graph = ConceptGraph()
