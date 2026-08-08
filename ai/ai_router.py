from ai.agents.gemini_agent import ask_gemini
from ai.agents.openai_agent import ask_openai
from ai.agents.deepseek_agent import ask_deepseek


def ask_ai(prompt, provider="gemini"):

    if provider == "gemini":
        return ask_gemini(prompt)

    elif provider == "openai":
        return ask_openai(prompt)

    elif provider == "deepseek":
        return ask_deepseek(prompt)

    else:
        return "Unknown AI Provider"