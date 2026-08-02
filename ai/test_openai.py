from ai.agents.openai_agent import ask_openai


def main():
    question = input("Ask OpenAI: ")
    answer = ask_openai(question)
    print("\nAnswer:\n")
    print(answer)


if __name__ == "__main__":
    main()
