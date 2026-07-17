from .goal_parser import GoalParser
from .task_manager import TaskManager
from .task import Task


class Planner:

    def __init__(self):

        self.goal_parser = GoalParser()
        self.task_manager = TaskManager()

    def create_plan(self, user_input):

        goal = self.goal_parser.parse(user_input)

        action = goal.get("action")

        if action == "open":

            task = Task(
                name=f"Open {goal['target']}",
                description=f"Launch {goal['target']}",
                tool=goal["tool"],
                priority=1,
                parameters={
                    "application": goal["target"]
                }
            )

            self.task_manager.add_task(task)

        elif action == "search":

            task = Task(
                name="Search Web",
                description=f"Search {goal['query']}",
                tool=goal["tool"],
                priority=1,
                parameters={
                    "query": goal["query"]
                }
            )

            self.task_manager.add_task(task)

        else:

            task = Task(
                name="AI Chat",
                description="General AI conversation",
                tool="ai",
                priority=1,
                parameters={
                    "prompt": user_input
                }
            )

            self.task_manager.add_task(task)

        return self.task_manager.tasks