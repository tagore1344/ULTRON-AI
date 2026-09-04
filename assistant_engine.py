# assistant_engine.py

from core.brain.ai_brain import AIBrain
from core.speech.speech_engine import SpeechEngine
from core.intent.intent_router import IntentRouter
from core.tools.tool_registry import ToolRegistry
from core.agent.async_agent_loop import AsyncAgentLoop


class AssistantEngine:
    """Top-level ULTRON runtime with backward-compatible agent execution."""

    # Explicit signals for tasks that benefit from planning and verification.
    _AGENT_SIGNALS = (
        "build ", "create ", "develop ", "implement ", "debug ",
        "fix ", "refactor ", "analyze ", "research ", "design ",
        "project", "code", "program", "multiple steps", "step by step",
    )

    def __init__(self):
        self.brain = AIBrain()
        self.speech = SpeechEngine()
        self.router = IntentRouter()
        self.tools = ToolRegistry()
        self.agent = AsyncAgentLoop(
            brain=self.brain,
            tools=self.tools,
            router=self.router,
        )

    def _should_agent(self, user_input: str, intent_data: dict) -> bool:
        if intent_data.get("intent") != "chat":
            return False
        text = user_input.strip().lower()
        return any(signal in text for signal in self._AGENT_SIGNALS)

    async def process(self, user_input: str):
        intent_data = self.router.detect(user_input)
        print(f"[INTENT] {intent_data}")

        if intent_data.get("intent") != "chat":
            return await self.tools.execute(intent_data)

        if self._should_agent(user_input, intent_data):
            response, state = await self.agent.run(user_input)
            print(f"[AGENT] task={state.task_id} status={state.status} steps={len(state.plan)}")
            return response

        return self.brain.think(user_input)

    async def speak_response(self, text):
        self.speech.speak(text)

    async def run_once(self, text):
        response = await self.process(text)
        await self.speak_response(response)
        return response
