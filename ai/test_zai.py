from ai.agents.zai_agent import ask_zai

print("=" * 50)
print("          Z AI TEST")
print("=" * 50)

question = input("\nAsk ZAI : ")

answer = ask_zai(question)

print("\nAnswer:\n")

print(answer)