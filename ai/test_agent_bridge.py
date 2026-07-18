from speech_engine_advanced import AdvancedSpeechEngine
from ai.agent_bridge import AgentBridge

speech = AdvancedSpeechEngine()

bridge = AgentBridge(speech)

while True:

    user = input("You: ")

    if user.lower() == "exit":
        break

    result = bridge.process(user)

    print(result)