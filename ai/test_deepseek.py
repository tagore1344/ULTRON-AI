from deepseek_client import ask_deepseek

question = input("Ask DeepSeek: ")

answer = ask_deepseek(question)

print("\nAnswer:\n")
print(answer)