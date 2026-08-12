import os

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False

try:
    import google.generativeai as genai
except Exception:
    genai = None

_model = None
_initialized = False


def _get_model():
    """Lazily configure genai and initialize the model on first use to prevent import race conditions."""
    global _model, _initialized
    if _initialized:
        return _model

    _initialized = True

    if genai is None:
        return None

    # Resolve absolute path to root .env file to ensure reliable loading across execution contexts
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        env_path = os.path.join(root_dir, ".env")
        load_dotenv(env_path)
    except Exception:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel("gemini-2.5-flash")
        return _model
    except Exception:
        return None


def ask_gemini(prompt: str) -> str:
    current_model = _get_model()

    if current_model is None:
        # Determine the root cause to return a clear, precise configuration error
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            env_path = os.path.join(root_dir, ".env")
            load_dotenv(env_path)
        except Exception:
            load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Gemini Error: GEMINI_API_KEY is not configured in your .env file."
        if genai is None:
            return "Gemini Error: google-generativeai package is not installed."
        return "Gemini Error: Failed to configure Gemini API client."

    try:
        response = current_model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Gemini Error: {str(e)}"
