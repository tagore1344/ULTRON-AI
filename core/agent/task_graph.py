# core/agent/task_graph.py
from enum import Enum
from typing import List, Dict, Any


class NodeState(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class TaskNode:
    """Represents a single executable node inside the agent's DAG task graph."""

    def __init__(self, node_id: str, label: str, intent: str, target: str, dependencies: List[str] = None):
        self.id = node_id
        self.label = label
        self.intent = intent
        self.target = target
        self.state = NodeState.READY
        self.dependencies = dependencies or []
        self.retries = 0
        self.max_retries = 2


class TaskGraph:
    """Directed Acyclic Graph (DAG) tracking multi-step execution flows statefully."""

    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode):
        self.nodes[node.id] = node

    def get_ready_nodes(self) -> List[TaskNode]:
        """Returns nodes whose dependencies have all completed successfully."""
        ready = []
        for node in self.nodes.values():
            if node.state != NodeState.READY:
                continue

            # Check if all dependencies succeeded
            deps_ok = True
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.state != NodeState.SUCCESS:
                    deps_ok = False
                    break

            if deps_ok:
                ready.append(node)
        return ready

    def propagate_failure(self, failed_node_id: str):
        """Statefully blocks child dependencies if an upstream node fails permanently."""
        for node in self.nodes.values():
            if failed_node_id in node.dependencies and node.state == NodeState.READY:
                node.state = NodeState.BLOCKED
                self.propagate_failure(node.id)

    def cancel_all(self):
        """Marks all pending or running nodes as CANCELLED statefully."""
        for node in self.nodes.values():
            if node.state in (NodeState.READY, NodeState.RUNNING):
                node.state = NodeState.CANCELLED

    def is_complete(self) -> bool:
        """Returns True if all nodes have reached a terminal state."""
        for node in self.nodes.values():
            if node.state in (NodeState.READY, NodeState.RUNNING):
                return False
        return True

    def has_failures(self) -> bool:
        """Returns True if any node failed to complete successfully."""
        for node in self.nodes.values():
            if node.state in (NodeState.FAILED, NodeState.CANCELLED, NodeState.BLOCKED):
                return True
        return False
