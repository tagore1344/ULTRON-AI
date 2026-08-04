import os

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return False

try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()

model = None
if genai is not None:
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.5-flash")
    except Exception:
        model = None


def ask_gemini(prompt: str) -> str:
    if model is None:
        return "Gemini Error: API dependency is unavailable in this environment."

    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Gemini Error: {str(e)}"