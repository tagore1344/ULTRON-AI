# core/agent/goal_manager.py
import datetime
from typing import Optional
from core.agent.task_graph import TaskGraph


class Goal:
    """Represents a long-horizon user-defined or autonomous goal."""

    def __init__(self, goal_id: str, description: str, priority: str = "MEDIUM"):
        self.id = goal_id
        self.description = description
        self.priority = priority
        self.created_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.is_cancelled = False
        self.graph: Optional[TaskGraph] = None


class GoalManager:
    """Manages active goal lifecycles, prioritization, and cancellation triggers."""

    def __init__(self):
        self.active_goal: Optional[Goal] = None

    def set_goal(self, goal_id: str, description: str, priority: str = "MEDIUM") -> Goal:
        """Create and register a new active goal."""
        self.active_goal = Goal(goal_id, description, priority)
        return self.active_goal

    def cancel_goal(self) -> bool:
        """Cancel the currently active goal and cascade cancellations to the task graph."""
        if self.active_goal:
            self.active_goal.is_cancelled = True
            if self.active_goal.graph:
                self.active_goal.graph.cancel_all()
            return True
        return False

    def clear_goal(self):
        self.active_goal = None


goal_manager = GoalManager()
