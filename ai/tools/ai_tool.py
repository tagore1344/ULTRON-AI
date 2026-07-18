from .base_tool import BaseTool
from ai.agents.gemini_agent import ask_gemini


class AITool(BaseTool):

    def __init__(self):
        super().__init__("ai")

    def execute(self, task):

        prompt = task.parameters.get("prompt", "")

        if not prompt:
            return "No prompt provided."

        response = ask_gemini(prompt)

        print("\n========== AI ==========\n")
        print(response)
        print("\n========================\n")

        return response