from ai.mock_speech import MockSpeech
from ai.agent_bridge import AgentBridge

speech = MockSpeech()

bridge = AgentBridge(speech)

while True:

    user = input("\nYou : ")

    if user.lower() == "exit":
        break

    result = bridge.process(user)

    print(result)