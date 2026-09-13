import os

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return False

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

client = None
if OpenAI is not None:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        client = None


def is_openai_available() -> bool:
    """Reports whether the OpenAI provider can currently serve requests."""
    global client
    if client is not None:
        return True
    # Late reconfiguration pass: a key may have become available after import
    # (e.g. .env loaded later, or injected dynamically during runtime).
    if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception:
            client = None
    return client is not None


def ask_openai(prompt: str) -> str:
    if client is None:
        return "OpenAI Error: API dependency is unavailable in this environment."

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are ULTRON AI, an advanced AI assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"OpenAI Error: {str(e)}"