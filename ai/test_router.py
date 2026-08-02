from ai.ai_router import ask_ai


def main():
    question = input("Ask ULTRON AI: ")
    answer = ask_ai(question, provider="gemini")
    print("\nULTRON:\n")
    print(answer)


if __name__ == "__main__":
    main()
