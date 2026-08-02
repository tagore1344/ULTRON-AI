from ai.agents.deepseek_agent import ask_deepseek


def main():
    question = input("Ask DeepSeek: ")
    answer = ask_deepseek(question)
    print("\nAnswer:\n")
    print(answer)


if __name__ == "__main__":
    main()
