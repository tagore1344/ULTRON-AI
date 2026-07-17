class GoalParser:
    """
    Converts a user's request into a structured goal.
    """

    def parse(self, user_input: str):

        text = user_input.lower().strip()

        if text.startswith("open "):

            target = text.replace("open ", "", 1)

            return {
                "action": "open",
                "target": target,
                "tool": "app_launcher"
            }

        elif text.startswith("close "):

            target = text.replace("close ", "", 1)

            return {
                "action": "close",
                "target": target,
                "tool": "app_launcher"
            }

        elif text.startswith("search "):

            query = text.replace("search ", "", 1)

            return {
                "action": "search",
                "query": query,
                "tool": "web_search"
            }

        return {
            "action": "chat",
            "prompt": user_input,
            "tool": "ai"
        }
