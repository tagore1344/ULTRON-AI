from dataclasses import dataclass, field
from typing import List


@dataclass
class ExecutionContext:
    """
    Stores the current execution state of ULTRON.
    """

    current_task: str = ""

    status: str = "idle"

    completed_tasks: List[str] = field(default_factory=list)

    failed_tasks: List[str] = field(default_factory=list)

    retry_count: int = 0

    def start(self, task_name):

        self.current_task = task_name

        self.status = "running"

    def complete(self):

        self.completed_tasks.append(
            self.current_task
        )

        self.status = "completed"

    def fail(self):

        self.failed_tasks.append(
            self.current_task
        )

        self.status = "failed"

    def reset(self):

        self.current_task = ""

        self.status = "idle"

        self.retry_count = 0