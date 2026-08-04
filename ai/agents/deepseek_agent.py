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
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
    except Exception:
        client = None


def ask_deepseek(prompt: str) -> str:
    if client is None:
        return "DeepSeek Error: API dependency is unavailable in this environment."

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are ULTRON AI, an intelligent cybersecurity assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"DeepSeek Error: {str(e)}"