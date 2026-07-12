from tools.app_launcher import open_instagram

from ai.orchestrator.prompt_manager import PromptManager
from ai.orchestrator.model_selector import ModelSelector
from ai.orchestrator.response_merger import ResponseMerger
from ai.orchestrator.consensus_engine import ConsensusEngine

from ai.agents.gemini_agent import ask_gemini
# from ai.agents.deepseek_agent import ask_deepseek
# from ai.agents.openai_agent import ask_openai


class AIOrchestrator:

    def __init__(self):
        self.prompt_manager = PromptManager()
        self.model_selector = ModelSelector()
        self.response_merger = ResponseMerger()
        self.consensus_engine = ConsensusEngine()

    def ask(self, user_prompt):

        # Tool execution
        if "open instagram" in user_prompt.lower():
            return open_instagram()

        # AI processing
        prompt = self.prompt_manager.prepare_prompt(user_prompt)

        provider = self.model_selector.choose_model(prompt)

        responses = []

        if provider == "gemini":
            responses.append(
                ask_gemini(prompt)
            )

        # elif provider == "openai":
        #     responses.append(
        #         ask_openai(prompt)
        #     )

        # elif provider == "deepseek":
        #     responses.append(
        #         ask_deepseek(prompt)
        #     )

        merged = self.response_merger.merge(responses)

        final = self.consensus_engine.combine([merged])

        return final