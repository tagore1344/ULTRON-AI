from ai.mock_speech import MockSpeech
from ai.agent_pipeline import AgentPipeline

speech = MockSpeech()

pipeline = AgentPipeline(speech)

while True:

    user = input("\nYou : ")

    if user.lower() == "exit":
        break

    result = pipeline.run(user)

    print("\n========== RESULT ==========\n")
    print(result)