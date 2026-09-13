import os
from unittest.mock import patch, MagicMock
from gemini_client import ask_gemini
import ai.agents.gemini_agent as agent


<<<<<<< HEAD
def test_gemini_is_not_initialized_at_import():
    """Verify that the Gemini model is NOT configured or initialized at module-import time."""
    # Reset internal initialization states for the test run
    agent._model = None
    agent._initialized = False

=======
def _reset_agent():
    """Resets the agent's lazy-init state for isolation between tests."""
    agent._model = None
    agent._initialized = False
    agent._backend = None


def test_gemini_is_not_initialized_at_import():
    """Verify that the Gemini model is NOT configured or initialized at module-import time."""
    _reset_agent()
>>>>>>> feature/astra-class-agent-core
    assert agent._model is None
    assert agent._initialized is False


<<<<<<< HEAD
@patch("google.generativeai.configure")
@patch("google.generativeai.GenerativeModel")
@patch("os.getenv")
def test_gemini_reads_api_key_on_request(mock_getenv, mock_model, mock_configure):
    """Verify that os.getenv('GEMINI_API_KEY') is called only when ask_gemini() is triggered."""
    agent._model = None
    agent._initialized = False

    # Mock environment variable and model instances
    mock_getenv.side_effect = lambda key, default=None: "mock_api_key_123" if key in ("GEMINI_API_KEY", "GOOGLE_API_KEY") else None
    mock_model.return_value = MagicMock()

    # Triggering query must dynamically read key and configure client
    ask_gemini("Test prompt")

    mock_getenv.assert_any_call("GEMINI_API_KEY")
    mock_configure.assert_called_with(api_key="mock_api_key_123")
    mock_model.assert_called_with("gemini-2.5-flash")
=======
@patch("os.getenv")
def test_gemini_reads_api_key_on_request(mock_getenv):
    """Modern SDK backend: key read lazily and used to build the genai Client."""
    _reset_agent()

    mock_getenv.side_effect = (
        lambda key, default=None: "mock_api_key_123"
        if key in ("GEMINI_API_KEY", "GOOGLE_API_KEY")
        else None
    )

    with patch("ai.agents.gemini_agent._new_genai.Client", return_value=MagicMock()) as mock_client:
        ask_gemini("Test prompt")

    mock_client.assert_called_with(api_key="mock_api_key_123")
>>>>>>> feature/astra-class-agent-core


@patch("os.getenv")
def test_gemini_missing_key_returns_clear_error(mock_getenv):
    """Verify that a missing GEMINI_API_KEY returns a clear application-level error instead of crashing."""
<<<<<<< HEAD
    agent._model = None
    agent._initialized = False

    # Simulate empty environment variable
=======
    _reset_agent()
>>>>>>> feature/astra-class-agent-core
    mock_getenv.return_value = None

    result = ask_gemini("Test prompt")

    assert "Gemini Error: GEMINI_API_KEY is not configured in your .env file." in result
<<<<<<< HEAD
=======


def test_gemini_genai_backend_generate_content():
    """Verify the modern google-genai backend calls models.generate_content correctly."""
    _reset_agent()
    agent._backend = "genai"
    agent._initialized = True

    mock_model = MagicMock()
    mock_model.models.generate_content.return_value = MagicMock(text="Hello from genai")
    agent._model = mock_model

    result = ask_gemini("Say hello")
    assert result == "Hello from genai"
    mock_model.models.generate_content.assert_called_with(
        model="gemini-2.5-flash", contents="Say hello"
    )


def test_gemini_legacy_backend_fallback():
    """Verify the legacy EOL SDK path still works when the backend is legacy."""
    _reset_agent()
    agent._backend = "legacy"
    agent._initialized = True

    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="Hello from legacy")
    agent._model = mock_model

    result = ask_gemini("Say hello")
    assert result == "Hello from legacy"
    mock_model.generate_content.assert_called_with("Say hello")

>>>>>>> feature/astra-class-agent-core
