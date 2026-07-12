from gemini_client import ask_gemini

# Uncomment these after they are working
# from openai_client import ask_openai
# from deepseek_client import ask_deepseek


def ask_ai(prompt, provider="gemini"):

    if provider == "gemini":
        return ask_gemini(prompt)

    # elif provider == "openai":
    #     return ask_openai(prompt)

    # elif provider == "deepseek":
    #     return ask_deepseek(prompt)

    else:
        return "Unknown AI Provider"