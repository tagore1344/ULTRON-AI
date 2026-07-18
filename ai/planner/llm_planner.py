import json

from ai.agents.gemini_agent import ask_gemini


class LLMPlanner:

    def __init__(self):
        pass

    def create_prompt(self, user_input):

        return f"""
You are ULTRON's planning engine.

Convert the user's request into a JSON array.

Return ONLY valid JSON.

Rules:

1. General conversation, greetings, explanations and questions
   -> action = "answer"

Example:
User: What is your name?

Output:
[
    {{
        "action":"answer",
        "query":"What is your name?"
    }}
]

Example:
User: Explain Python decorators

Output:
[
    {{
        "action":"answer",
        "query":"Explain Python decorators"
    }}
]

2. Open applications

Example:
User: Open Chrome

Output:
[
    {{
        "action":"open",
        "target":"chrome"
    }}
]

3. Close applications

Example:
User: Close Chrome

Output:
[
    {{
        "action":"close",
        "target":"chrome"
    }}
]

4. Explicit web searches ONLY

Example:
User: Search Google for Python decorators

Output:
[
    {{
        "action":"search",
        "target":"google",
        "query":"Python decorators"
    }}
]

Example:
User: Search YouTube for AI

Output:
[
    {{
        "action":"search",
        "target":"youtube",
        "query":"AI"
    }}
]

Example:
User: Search GitHub for LangChain

Output:
[
    {{
        "action":"search",
        "target":"github",
        "query":"LangChain"
    }}
]

Example:
User: Search Wikipedia for Linux

Output:
[
    {{
        "action":"search",
        "target":"wikipedia",
        "query":"Linux"
    }}
]

Never use "search" for normal questions.

User:
{user_input}
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

        try:
            plan = json.loads(response)
        except json.JSONDecodeError:
            return [
                {
                    "action": "answer",
                    "query": user_input
                }
            ]

        return self.normalize_plan(plan)