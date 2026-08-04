# core/brain/ai_brain.py — AI brain that delegates to the orchestrator
try:
    from ai.orchestrator.ai_orchestrator import AIOrchestrator
except Exception:
    AIOrchestrator = None


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
        if self.orchestrator is not None:
            try:
                return self.orchestrator.ask(user_input)
            except Exception as e:
                return f"Brain error: {str(e)}"
        return "ULTRON Brain is not available in this environment."