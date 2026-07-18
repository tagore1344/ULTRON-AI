import json

from ai.agents.gemini_agent import ask_gemini


class LLMPlanner:

    def create_plan(self, user_request):

        prompt = f"""
You are an AI Planner.

Convert the user's request into JSON.

Return ONLY valid JSON.

Example:

[
    {{
        "action": "open",
        "target": "chrome"
    }},
    {{
        "action": "search",
        "query": "python tutorial"
    }}
]

User Request:

{user_request}
"""

        response = ask_gemini(prompt)

        print("\n===== GEMINI RESPONSE =====\n")
        print(response)
        print("\n===========================\n")

        # Remove markdown code fences if present
        response = response.strip()

        if response.startswith("```json"):
            response = response.replace("```json", "", 1)

        if response.startswith("```"):
            response = response.replace("```", "", 1)

        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:

            plan = json.loads(response)

            return plan

        except Exception as e:

            print("JSON Error:", e)

            return []