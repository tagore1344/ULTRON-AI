from ai.agents.gemini_agent import ask_gemini


def main():
    question = input("Ask Gemini: ")
    answer = ask_gemini(question)
    print("\nAnswer:\n")
    print(answer)


if __name__ == "__main__":
    main()
