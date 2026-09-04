"""Small, model-agnostic planner used by ULTRON's agent loop."""
from __future__ import annotations

from typing import List


class TaskPlanner:
    """Turn a user goal into explicit, verifiable execution steps.

    A model-backed planner can subclass this interface later. The deterministic
    fallback is intentionally conservative and useful for simple requests.
    """

    def plan(self, goal: str) -> List[str]:
        goal = goal.strip()
        if not goal:
            return []

        lower = goal.lower()
        steps = ["Understand the requested outcome and constraints."]

        if any(word in lower for word in ("code", "program", "bug", "debug", "project")):
            steps += [
                "Inspect the relevant project files and existing implementation.",
                "Implement the smallest correct change.",
                "Run relevant tests or validation commands.",
                "Inspect failures and iterate until verification passes.",
            ]
        elif any(word in lower for word in ("research", "find", "compare", "analyze")):
            steps += [
                "Gather the required evidence or inputs.",
                "Evaluate the evidence against the goal.",
                "Produce a concise, verifiable result.",
            ]
        else:
            steps += [
                "Determine the actions required to satisfy the goal.",
                "Execute the required actions.",
                "Verify the result against the original goal.",
            ]

        return steps
