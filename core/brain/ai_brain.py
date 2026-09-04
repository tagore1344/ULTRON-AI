# core/brain/ai_brain.py — AI brain that delegates to the orchestrator
try:
    from ai.orchestrator.ai_orchestrator import AIOrchestrator
except Exception:
    AIOrchestrator = None


class AIBrain:
    """The brain of ULTRON AI — reasoning plus autonomous action."""

    def __init__(self):
        self.orchestrator = None
        if AIOrchestrator is not None:
            try:
                self.orchestrator = AIOrchestrator()
            except Exception as exc:
                print(f"[BRAIN] Orchestrator init failed: {exc}")

    def think(self, user_input: str) -> str:
        """Generate a response for the given user input."""
        if self.orchestrator is not None:
            try:
                return self.orchestrator.ask(user_input)
            except Exception as exc:
                return f"Brain error: {exc}"
        return "ULTRON Brain is not available in this environment."

    def act(self, goal: str) -> str:
        """Execute a multi-step goal using the configured agent runtime."""
        if self.orchestrator is not None:
            try:
                return self.orchestrator.act(goal)
            except Exception as exc:
                return f"Brain action error: {exc}"
        return "ULTRON Brain is not available in this environment."
