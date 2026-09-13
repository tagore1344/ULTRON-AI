<<<<<<< HEAD
"""Model orchestration for ULTRON."""
from __future__ import annotations

import os
=======
import os
import time
import logging
>>>>>>> origin/main

from ai.orchestrator.prompt_manager import PromptManager
from ai.orchestrator.model_selector import ModelSelector
from ai.orchestrator.response_merger import ResponseMerger
from ai.orchestrator.consensus_engine import ConsensusEngine
<<<<<<< HEAD
from ai.agents.gemini_agent import ask_gemini

try:
    from core.agent.astra_agent import AstraAgent
except Exception:
    AstraAgent = None


class AIOrchestrator:
    """Route ordinary reasoning and autonomous tasks through the best provider."""
=======

logger = logging.getLogger("ultron-api")

try:
    from ai.agents.gemini_agent import ask_gemini
except Exception as e:  # pragma: no cover - import guard
    ask_gemini = None
    logger.error("Gemini agent unavailable: %s", e)

# PROJECT_REVIEW §5.1 — Multi-Model Consensus is now FULLY ACTIVATED.
# Each provider acts as a live fallback for the routed primary provider.
try:
    from ai.agents.deepseek_agent import ask_deepseek
except Exception as e:  # pragma: no cover - import guard
    ask_deepseek = None
    logger.error("DeepSeek agent unavailable: %s", e)

try:
    from ai.agents.openai_agent import ask_openai
except Exception as e:  # pragma: no cover - import guard
    ask_openai = None
    logger.error("OpenAI agent unavailable: %s", e)


PROVIDER_ASKS = {
    "gemini": lambda: ask_gemini,
    "openai": lambda: ask_openai,
    "deepseek": lambda: ask_deepseek,
}

# Markers that identify a degraded/error answer string coming from an agent.
ERROR_MARKERS = ("Error:", "unavailable in this environment")


class AIOrchestrator:
    """Multi-provider orchestration layer.

    Modes:
      * "fallback" (default): the ModelSelector picks the best provider for the
        prompt; on failure or unavailability, remaining providers are tried in
        strategic order until one succeeds.
      * "multi": every available provider answers; responses are merged by the
        ResponseMerger and consolidated by the ConsensusEngine.

    The mode is controlled with ULTRON_CONSENSUS_MODE=fallback|multi.
    """
>>>>>>> origin/main

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

<<<<<<< HEAD
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
=======
    # ────────────────────────────────────────────────────────────────────────
    # PROVIDER EXECUTION HELPERS
    # ────────────────────────────────────────────────────────────────────────

    def _ask_provider(self, provider: str, prompt: str) -> str:
        """Dispatches a prompt to a named provider. Returns the raw answer."""
        ask_fn = PROVIDER_ASKS.get(provider, lambda: None)()
        if ask_fn is None:
            return f"{provider.capitalize()} Error: provider module failed to load."
        try:
            return str(ask_fn(prompt))
        except Exception as e:
            return f"{provider.capitalize()} Error: {e}"

    def _is_failure(self, response: str) -> bool:
        if not response or not response.strip():
            return True
        lowered = response.lower()
        return any(marker.lower() in lowered for marker in ERROR_MARKERS)

    def _collect_success(self, ordered_providers, prompt):
        """Tries providers in order. Returns (successful_answer|None, collected_errors)."""
        errors = []
        for provider in ordered_providers:
            start = time.perf_counter()
            response = self._ask_provider(provider, prompt)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info("PROVIDER_CALL provider=%s latency_ms=%.1f", provider, elapsed_ms)
            if not self._is_failure(response):
                return response, errors
            errors.append(response)
            logger.warning("Provider '%s' failed for request; trying next.", provider)
        return None, errors

    # ────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ────────────────────────────────────────────────────────────────────────

    def ask(self, user_prompt):

        if not user_prompt or not str(user_prompt).strip():
            return "ULTRON Error: empty prompts cannot be processed."

        # AI processing
        prompt = self.prompt_manager.prepare_prompt(str(user_prompt).strip())

        ranked = self.model_selector.rank_models(prompt)

        mode = os.getenv("ULTRON_CONSENSUS_MODE", "fallback").strip().lower()

        if mode == "multi":
            responses = []
            collected_errors = []
            for provider in ranked:
                response = self._ask_provider(provider, prompt)
                if not self._is_failure(response):
                    responses.append(response)
                else:
                    collected_errors.append(response)
                    logger.warning("Provider '%s' skipped during consensus build.", provider)

            if not responses:
                return (
                    "ULTRON Error: no AI providers succeeded.\n"
                    + "\n".join(collected_errors)
                )

            merged = self.response_merger.merge(responses)
            final = self.consensus_engine.combine([merged])
            return final

        # Default single-pass cascade with automatic provider fallbacks.
        final_answer, failures = self._collect_success(ranked, prompt)

        if final_answer is not None:
            merged = self.response_merger.merge([final_answer])
            final = self.consensus_engine.combine([merged])
            return final

        # Every provider failed or lacks keys: fail-soft with actionable output.
        detail = "\n".join(failures) if failures else "No providers configured."
        return f"ULTRON Error: all AI providers failed to respond.\n{detail}"
>>>>>>> origin/main
