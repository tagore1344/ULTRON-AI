from ai.orchestrator.ai_orchestrator import AIOrchestrator

brain = AIOrchestrator()

print("=" * 50)
print("         ULTRON AI")
print("=" * 50)

while True:

    question = input("\nYou: ")

    if question.lower() == "exit":
        break

    answer = brain.ask(question)

    print("\nULTRON:\n")
    print(answer)