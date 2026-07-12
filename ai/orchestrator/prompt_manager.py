class PromptManager:

    def prepare_prompt(self, user_prompt):

        system_prompt = """
You are ULTRON AI.

You are an advanced AI assistant.

Always answer accurately.

Explain your reasoning clearly.

If multiple solutions exist, recommend the best one.

Never hallucinate.

Always think step by step.
"""

        final_prompt = f"{system_prompt}\n\nUser:\n{user_prompt}"

        return final_prompt
