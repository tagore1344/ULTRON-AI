"""State primitives for ULTRON's agent execution loop.

The state is deliberately serialisable so a future persistent store can replace
this in-memory implementation without changing the agent contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class TaskState:
    goal: str
    task_id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "pending"
    plan: List[str] = field(default_factory=list)
    current_step: int = 0
    observations: List[str] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_action(self, name: str, arguments: Dict[str, Any]) -> None:
        self.actions.append({"name": name, "arguments": arguments})

    def record_result(self, result: Any, ok: bool = True) -> None:
        self.results.append({"ok": ok, "result": result})

    def fail(self, error: str) -> None:
        self.errors.append(error)
        self.status = "failed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
