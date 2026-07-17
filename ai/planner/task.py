from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Task:
    """
    Represents one executable task for ULTRON.
    """

    name: str
    description: str
    tool: str

    priority: int = 1
    status: str = "pending"

    parameters: Dict[str, Any] = field(default_factory=dict)

    def start(self):
        self.status = "running"

    def complete(self):
        self.status = "completed"

    def fail(self):
        self.status = "failed"

    def to_dict(self):

        return {
            "name": self.name,
            "description": self.description,
            "tool": self.tool,
            "priority": self.priority,
            "status": self.status,
            "parameters": self.parameters,
        }

    def __str__(self):

        return (
            f"Task("
            f"name='{self.name}', "
            f"tool='{self.tool}', "
            f"status='{self.status}')"
        )