from ai.models.task import Task
from ai.planner.action_mapper import ACTION_MAP


class TaskBuilder:

    def __init__(self):
        pass

    def build(self, plan):

        tasks = []

        required = {
            "answer": ["query"],
            "open": ["target"],
            "close": ["target"],
            "google_search": ["query"],
            "youtube_search": ["query"],
            "github_search": ["query"],
            "wikipedia_search": ["query"],
        }

        for item in plan:

            action = item.get("action")

            if action is None:
                raise ValueError("Planner returned an action without 'action' field.")

            # Validate required fields
            fields = required.get(action, [])

            for field in fields:
                if field not in item:
                    raise ValueError(
                        f"Planner returned invalid action '{action}': missing '{field}'"
                    )

            # Map action -> tool
            tool = ACTION_MAP.get(action)

            if tool is None:
                raise ValueError(f"Unknown action '{action}'")

            # Build task
            task = Task(
                name=action.replace("_", " ").title(),
                description=item.get("query", item.get("target", "")),
                tool=tool,
                priority=1,
                status="pending",
                parameters=item
            )

            tasks.append(task)

        return tasks