# core/neural/event_memory.py
import datetime
from typing import Dict, Any, Optional

from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralNodeModel


class EventMemory:
    """Manages discrete stateful execution and environmental occurrences in the Neural Graph."""

    def __init__(self):
        pass

    def record_event(self, event_id: str, label: str, properties: Dict[str, Any] = None) -> bool:
        """Saves a discrete environmental event or execution outcome node."""
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        node = NeuralNodeModel(
            node_id=event_id,
            node_type="EVENT",
            label=label,
            properties=properties or {},
            belief_confidence=1.0, # Factual observed events carry 1.0 confidence
            operational_state="KNOWN",
            last_updated=now_str
        )
        return neural_memory.save_node(node)

    def record_state(self, state_id: str, label: str, belief_confidence: float = 0.5, properties: Dict[str, Any] = None) -> bool:
        """Saves an environmental or helper state variable node."""
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        node = NeuralNodeModel(
            node_id=state_id,
            node_type="STATE",
            label=label,
            properties=properties or {},
            belief_confidence=belief_confidence,
            operational_state="UNVERIFIED",
            last_updated=now_str
        )
        node.operational_state = node.evaluate_operational_state()
        return neural_memory.save_node(node)


# Singleton instance
event_memory = EventMemory()
