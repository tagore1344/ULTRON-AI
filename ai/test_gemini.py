from gemini_client import ask_gemini

question = input("Ask Gemini: ")

answer = ask_gemini(question)

print("\nAnswer:\n")
print(answer)