from .goal_parser import GoalParser
from .task_manager import TaskManager
from .task import Task


class Planner:

    def __init__(self):

        self.goal_parser = GoalParser()
        self.task_manager = TaskManager()

    def create_plan(self, user_input):

        # Start with a fresh task list for every request
        self.task_manager = TaskManager()

        text = user_input.lower().strip()

        # Split multiple commands connected with "and"
        if " and " in text:
            commands = [cmd.strip() for cmd in text.split(" and ")]
        else:
            commands = [text]

        priority = 1

        for command in commands:

            goal = self.goal_parser.parse(command)

            action = goal.get("action")

            if action == "open":

                task = Task(
                    name=f"Open {goal['target']}",
                    description=f"Launch {goal['target']}",
                    tool=goal["tool"],
                    priority=priority,
                    parameters={
                        "application": goal["target"]
                    }
                )

            elif action == "close":

                task = Task(
                    name=f"Close {goal['target']}",
                    description=f"Close {goal['target']}",
                    tool=goal["tool"],
                    priority=priority,
                    parameters={
                        "application": goal["target"]
                    }
                )

            elif action == "search":

                task = Task(
                    name="Search Web",
                    description=f"Search {goal['query']}",
                    tool=goal["tool"],
                    priority=priority,
                    parameters={
                        "query": goal["query"]
                    }
                )

            else:

                task = Task(
                    name="AI Chat",
                    description="General AI Conversation",
                    tool="ai",
                    priority=priority,
                    parameters={
                        "prompt": command
                    }
                )

            self.task_manager.add_task(task)

            priority += 1

        return self.task_manager.tasks