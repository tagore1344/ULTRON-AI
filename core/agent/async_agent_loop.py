"""Async agent loop that integrates ULTRON's existing brain and tools."""
from __future__ import annotations

from typing import Any, Optional

from core.intent.intent_router import IntentRouter
from core.tools.tool_registry import ToolRegistry

from .planner import TaskPlanner
from .task_state import TaskState


class AsyncAgentLoop:
    """Plan and execute multi-step goals while preserving existing routing."""

    def __init__(
        self,
        brain: Any,
        tools: Optional[ToolRegistry] = None,
        router: Optional[IntentRouter] = None,
        planner: Optional[TaskPlanner] = None,
    ) -> None:
        self.brain = brain
        self.tools = tools or ToolRegistry()
        self.router = router or IntentRouter()
        self.planner = planner or TaskPlanner()

    async def run(self, goal: str) -> tuple[str, TaskState]:
        state = TaskState(goal=goal)
        state.plan = self.planner.plan(goal)
        if not state.plan:
            state.fail("Cannot execute an empty goal.")
            return state.errors[-1], state

        state.status = "running"
        outputs: list[str] = []

        for index, step in enumerate(state.plan):
            state.current_step = index
            state.record_action("execute_step", {"step": step})
            try:
                # Reuse the existing intent/tool layer for concrete actions.
                intent_data = self.router.detect(step)
                if intent_data.get("intent") != "chat":
                    result = await self.tools.execute(intent_data)
                else:
                    result = self.brain.think(
                        "Work on this step as part of the larger goal. "
                        f"Goal: {goal}\nStep: {step}"
                    )
                text = str(result)
                outputs.append(text)
                state.record_result(text, True)
                state.observations.append(text)
            except Exception as exc:
                state.record_result(str(exc), False)
                state.fail(str(exc))
                return "ULTRON stopped after an execution failure: " + str(exc), state

        state.status = "completed"
        return outputs[-1] if outputs else "ULTRON completed the task.", state
