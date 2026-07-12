from ai_router import ask_ai

question = input("Ask ULTRON AI: ")

answer = ask_ai(question, provider="gemini")

print("\nULTRON:\n")
print(answer)