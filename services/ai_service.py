# services/ai_service.py — AI service layer
try:
    from ai.orchestrator.ai_orchestrator import AIOrchestrator
except Exception:
    AIOrchestrator = None

try:
    from ai_router import ask_ai
except Exception:
    ask_ai = None


class AIService:
    """Service layer for AI interactions — wraps the orchestrator and router."""

    def __init__(self):
        self.orchestrator = None
        if AIOrchestrator is not None:
            try:
                self.orchestrator = AIOrchestrator()
            except Exception as e:
                print(f"[AI SERVICE] Orchestrator init failed: {e}")

    def ask(self, prompt: str, provider: str = "gemini") -> str:
        """Send a prompt to the AI and return the response."""
        if self.orchestrator is not None:
            try:
                return self.orchestrator.ask(prompt)
            except Exception as e:
                return f"AI Service error: {str(e)}"

        if ask_ai is not None:
            try:
                return ask_ai(prompt, provider=provider)
            except Exception as e:
                return f"AI Service error: {str(e)}"

        return "AI Service is not available in this environment."