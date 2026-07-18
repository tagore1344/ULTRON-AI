import json

from ai.agents.gemini_agent import ask_gemini


class LLMPlanner:

    def __init__(self):
        pass

    def create_prompt(self, user_input):

        return f"""
You are an AI planner.

Convert the user's request into a JSON array.

Examples:

User:
Open Chrome

Output:
[
    {{
        "action":"open",
        "target":"chrome"
    }}
]

User:
Close Chrome

Output:
[
    {{
        "action":"close",
        "target":"chrome"
    }}
]

User:
Search Python decorators

Output:
[
    {{
        "action":"search",
        "query":"Python decorators"
    }}
]

User:
{user_input}

Return ONLY JSON.
"""

    def normalize_plan(self, plan):

        normalized = []

        for item in plan:

            action = item.get("action", "").lower()

            if action == "search":

                target = item.get("target", "").lower()

                if target == "youtube":

                    item["action"] = "youtube_search"

                elif target == "github":

                    item["action"] = "github_search"

                elif target == "wikipedia":

                    item["action"] = "wikipedia_search"

                else:

                    item["action"] = "google_search"

            normalized.append(item)

        return normalized

    def create_plan(self, user_input):

        prompt = self.create_prompt(user_input)

        response = ask_gemini(prompt)

        print("\n===== GEMINI RESPONSE =====\n")
        print(response)
        print("\n===========================\n")

        response = response.replace("```json", "")
        response = response.replace("```", "")
        response = response.strip()

        plan = json.loads(response)

        return self.normalize_plan(plan)