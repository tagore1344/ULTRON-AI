"""Model orchestration for ULTRON."""
from __future__ import annotations

import os

from ai.orchestrator.prompt_manager import PromptManager
from ai.orchestrator.model_selector import ModelSelector
from ai.orchestrator.response_merger import ResponseMerger
from ai.orchestrator.consensus_engine import ConsensusEngine
from ai.agents.gemini_agent import ask_gemini

try:
    from core.agent.astra_agent import AstraAgent
except Exception:
    AstraAgent = None


class AIOrchestrator:
    """Route ordinary reasoning and autonomous tasks through the best provider."""

    def __init__(self):
        self.prompt_manager = PromptManager()
        self.model_selector = ModelSelector()
        self.response_merger = ResponseMerger()
        self.consensus_engine = ConsensusEngine()
        self.astra = None
        if AstraAgent is not None:
            try:
                self.astra = AstraAgent()
            except Exception as exc:
                print(f"[ASTRA] init failed: {exc}")

    def ask(self, user_prompt: str) -> str:
        """Generate a response, preferring GPT-6 Astra when configured."""
        if self.astra is not None and self.astra.available() and os.getenv("ULTRON_USE_ASTRA", "1") == "1":
            return self.astra.run(user_prompt)

        prompt = self.prompt_manager.prepare_prompt(user_prompt)
        provider = self.model_selector.choose_model(prompt)
        responses = []
        if provider == "gemini":
            responses.append(ask_gemini(prompt))

        if not responses:
            return "No AI provider is configured. Set OPENAI_API_KEY to enable GPT-6 Astra."

        merged = self.response_merger.merge(responses)
        return self.consensus_engine.combine([merged])

    def act(self, goal: str) -> str:
        """Execute a multi-step goal with the Astra tool-using agent when available."""
        if self.astra is not None and self.astra.available():
            return self.astra.run(goal)
        return self.ask(goal)
