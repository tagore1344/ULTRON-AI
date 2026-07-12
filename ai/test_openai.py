from openai_client import ask_openai

question = input("Ask OpenAI: ")

answer = ask_openai(question)

print("\nAnswer:\n")
print(answer)