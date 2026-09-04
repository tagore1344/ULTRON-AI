"""Model-agnostic agent execution loop for ULTRON."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .planner import TaskPlanner
from .task_state import TaskState
from .verifier import Verifier


@dataclass
class AgentResult:
    success: bool
    state: TaskState
    output: Any = None


class AgentLoop:
    """Execute a goal through plan -> execute -> verify, with bounded retries."""

    def __init__(
        self,
        planner: Optional[TaskPlanner] = None,
        verifier: Optional[Verifier] = None,
        executor: Optional[Callable[[str, TaskState], Any]] = None,
        max_retries: int = 2,
    ) -> None:
        self.planner = planner or TaskPlanner()
        self.verifier = verifier or Verifier()
        self.executor = executor or self._default_executor
        self.max_retries = max(0, max_retries)

    @staticmethod
    def _default_executor(step: str, state: TaskState) -> Dict[str, Any]:
        # Planning is usable immediately; real tool execution is injected by the
        # ToolRegistry/agent integration rather than hidden inside the planner.
        return {"status": "planned", "step": step}

    def run(self, goal: str) -> AgentResult:
        state = TaskState(goal=goal)
        state.plan = self.planner.plan(goal)
        if not state.plan:
            state.fail("Cannot execute an empty goal.")
            return AgentResult(False, state)

        state.status = "running"
        output: Any = None

        for index, step in enumerate(state.plan):
            state.current_step = index
            attempts = 0
            while attempts <= self.max_retries:
                attempts += 1
                try:
                    state.record_action("execute_step", {"step": step, "attempt": attempts})
                    output = self.executor(step, state)
                    verification = self.verifier.verify(output)
                    state.record_result(verification.message, verification.ok)
                    if verification.ok:
                        break
                    if attempts > self.max_retries:
                        state.fail(verification.message)
                except Exception as exc:
                    state.record_result(str(exc), False)
                    if attempts > self.max_retries:
                        state.fail(str(exc))
            if state.status == "failed":
                return AgentResult(False, state, output)

        state.status = "completed"
        return AgentResult(True, state, output)
