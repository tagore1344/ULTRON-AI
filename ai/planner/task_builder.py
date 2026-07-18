from .task import Task


class TaskBuilder:

    def build(self, plan):

        tasks = []

        priority = 1

        for item in plan:

            action = item.get("action")

            # ----------------------------
            # Desktop Apps
            # ----------------------------

            if action == "open":

                task = Task(
                    name=f"Open {item['target']}",
                    description=f"Launch {item['target']}",
                    tool="app_launcher",
                    priority=priority,
                    parameters={
                        "application": item["target"],
                        "action": "open"
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

            # ----------------------------
            # Browser Searches
            # ----------------------------

            elif action == "google_search":

                task = Task(
                    name="Google Search",
                    description=item["query"],
                    tool="browser_automation",
                    priority=priority,
                    parameters={
                        "action": "google_search",
                        "query": item["query"]
                    }
                )

            elif action == "youtube_search":

                task = Task(
                    name="YouTube Search",
                    description=item["query"],
                    tool="browser_automation",
                    priority=priority,
                    parameters={
                        "action": "youtube_search",
                        "query": item["query"]
                    }
                )

            elif action == "github_search":

                task = Task(
                    name="GitHub Search",
                    description=item["query"],
                    tool="browser_automation",
                    priority=priority,
                    parameters={
                        "action": "github_search",
                        "query": item["query"]
                    }
                )

            elif action == "wikipedia_search":

                task = Task(
                    name="Wikipedia Search",
                    description=item["query"],
                    tool="browser_automation",
                    priority=priority,
                    parameters={
                        "action": "wikipedia_search",
                        "query": item["query"]
                    }
                )

            # ----------------------------
            # Browser URLs
            # ----------------------------

            elif action == "open_url":

                task = Task(
                    name="Open URL",
                    description=item["url"],
                    tool="browser_automation",
                    priority=priority,
                    parameters={
                        "action": "open_url",
                        "url": item["url"]
                    }
                )

            # ----------------------------
            # Unknown
            # ----------------------------

            else:

                task = Task(
                    name="Unknown Task",
                    description=str(item),
                    tool="unknown",
                    priority=priority,
                    parameters=item
                )

            tasks.append(task)

            priority += 1

        return tasks