from .task import Task


class TaskBuilder:

    def build(self, plan):

        tasks = []

        priority = 1

        websites = [
            "google",
            "youtube",
            "github",
            "linkedin",
            "gmail",
            "chatgpt",
            "claude",
            "deepseek",
            "stackoverflow",
            "wikipedia"
        ]

        for item in plan:

            action = item.get("action")

            if action == "open":

                target = item["target"].lower()

                if target in websites:

                    task = Task(
                        name=f"Open {target}",
                        description=f"Open {target}",
                        tool="browser",
                        priority=priority,
                        parameters={
                            "website": target
                        }
                    )

                else:

                    task = Task(
                        name=f"Open {target}",
                        description=f"Launch {target}",
                        tool="app_launcher",
                        priority=priority,
                        parameters={
                            "application": target,
                            "action": "open"
                        }
                    )

            elif action == "search":

                task = Task(
                    name="Search Web",
                    description=item["query"],
                    tool="web_search",
                    priority=priority,
                    parameters={
                        "query": item["query"]
                    }
                )

            elif action == "close":

                task = Task(
                    name=f"Close {item['target']}",
                    description=f"Close {item['target']}",
                    tool="app_launcher",
                    priority=priority,
                    parameters={
                        "application": item["target"],
                        "action": "close"
                    }
                )

            else:

                task = Task(
                    name="AI Chat",
                    description="General AI Conversation",
                    tool="ai",
                    priority=priority,
                    parameters=item
                )

            tasks.append(task)

            priority += 1

        return tasks