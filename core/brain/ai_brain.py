# core/brain/ai_brain.py — AI brain that delegates to the orchestrator
import time
import logging

try:
    from ai.orchestrator.ai_orchestrator import AIOrchestrator
except Exception:
    AIOrchestrator = None

logger = logging.getLogger("ultron-api")


def _request_id():
    try:
        from backend.logging_context import get_request_id
        return get_request_id()
    except Exception:
        return "cli"


class AIBrain:
    """The brain of ULTRON AI — processes user input and returns responses."""

    def __init__(self):
        self.orchestrator = None
        if AIOrchestrator is not None:
            try:
                self.orchestrator = AIOrchestrator()
            except Exception as e:
                print(f"[BRAIN] Orchestrator init failed: {e}")

    def think(self, user_input: str) -> str:
        """Generate a response for the given user input."""
        start = time.perf_counter()
        if self.orchestrator is not None:
            try:
                result = self.orchestrator.ask(user_input)
                logger.info(
                    "REASONED req=%s provider=lite latency_ms=%.1f",
                    _request_id(), (time.perf_counter() - start) * 1000,
                )
                return result
            except Exception as e:
                return f"Brain error: {str(e)}"
        return "ULTRON Brain is not available in this environment."