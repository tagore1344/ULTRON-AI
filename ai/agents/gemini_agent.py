import os
import warnings

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False

# ── Preferred: modern unified Google SDK (google-genai) ──
try:
    from google import genai as _new_genai
    GENAI_NEW_OK = _new_genai is not None
except Exception:
    _new_genai = None
    GENAI_NEW_OK = False

# ── Fallback: legacy End-of-Life SDK (google-generativeai) ──
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as _legacy_genai
    GENAI_LEGACY_OK = _legacy_genai is not None
except Exception:
    _legacy_genai = None
    GENAI_LEGACY_OK = False

_model = None
_backend = None  # "genai" (new SDK) or "legacy" (EOL SDK)
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


def _build_for_backend(api_key, backend):
    """Builds the SDK client/model for a chosen backend, or None on failure."""
    if backend == "genai" and GENAI_NEW_OK:
        try:
            return _new_genai.Client(api_key=api_key)
        except Exception:
            return None
    if backend == "legacy" and GENAI_LEGACY_OK:
        try:
            _legacy_genai.configure(api_key=api_key)
            return _legacy_genai.GenerativeModel("gemini-2.5-flash")
        except Exception:
            return None
    return None


def _build_model(api_key):
    """Selects the backend: explicit override -> preferred new SDK -> legacy fallback."""
    global _backend

    forced = (os.getenv("ULTRON_GEMINI_SDK") or "").strip().lower()
    if forced in ("genai", "legacy"):
        _backend = forced
        return _build_for_backend(api_key, forced)

    if GENAI_NEW_OK:
        _backend = "genai"
        model = _build_for_backend(api_key, "genai")
        if model is not None:
            return model

    if GENAI_LEGACY_OK:
        _backend = "legacy"
        return _build_for_backend(api_key, "legacy")

    _backend = None
    return None


def _get_model():
    """Lazily configure the SDK and initialize the model on first use to prevent import race conditions."""
    global _model, _initialized
    if _initialized:
        return _model

    _initialized = True
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
        if not GENAI_NEW_OK and not GENAI_LEGACY_OK:
            return "Gemini Error: Neither google-genai nor google-generativeai is installed."
        return "Gemini Error: Failed to configure Gemini API client."

    try:
        if _backend == "genai":
            response = current_model.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text
        # Legacy SDK backend
        response = current_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini Error: {str(e)}"

