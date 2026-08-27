import os
import warnings

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False

try:
    # google-generativeai is End-of-Life upstream; suppress its startup FutureWarning
    # until the migration to the unified `google-genai` SDK is completed.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai
except Exception:
    genai = None

_model = None
_initialized = False


def _resolve_api_key():
    """Reads the Gemini credentials from the environment without leaking values."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _load_root_env():
    """Resolve absolute path to root .env file to ensure reliable loading across execution contexts."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        env_path = os.path.join(root_dir, ".env")
        load_dotenv(env_path)
    except Exception:
        load_dotenv()


def _build_model(api_key):
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception:
        return None


def _get_model():
    """Lazily configure genai and initialize the model on first use to prevent import race conditions."""
    global _model, _initialized
    if _initialized:
        return _model

    _initialized = True

    if genai is None:
        return None

    _load_root_env()

    api_key = _resolve_api_key()
    if not api_key:
        return None

    _model = _build_model(api_key)
    return _model


def is_gemini_available() -> bool:
    """Cheap non-network probe: reports whether the Gemini provider can serve requests."""
    if _initialized:
        return _model is not None
    return _get_model() is not None


def ask_gemini(prompt: str) -> str:
    current_model = _get_model()

    if current_model is None:
        # Determine the root cause to return a clear, precise configuration error
        _load_root_env()

        api_key = _resolve_api_key()
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
