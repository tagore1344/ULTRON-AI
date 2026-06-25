# assistant_engine.py

import asyncio
from core.brain.ai_brain import AIBrain
from core.speech.speech_engine import SpeechEngine
from core.intent.intent_router import IntentRouter
from core.tools.tool_registry import ToolRegistry


class AssistantEngine:

    def __init__(self):

        self.brain = AIBrain()

        self.speech = SpeechEngine()

        self.router = IntentRouter()

        self.tools = ToolRegistry()

    async def process(self, user_input: str):

        # Detect intent
        intent_data = self.router.detect(user_input)

        print(f"[INTENT] {intent_data}")

        # Execute tool
        if intent_data["intent"] != "chat":

            result = await self.tools.execute(
                intent_data
            )

            return result

        # Otherwise AI response
        response = self.brain.think(user_input)

        return response

    async def speak_response(self, text):

        self.speech.speak(text)

    async def run_once(self, text):

        response = await self.process(text)

        await self.speak_response(response)

        return response