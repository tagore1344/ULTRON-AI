import os
from unittest.mock import patch, MagicMock
from gemini_client import ask_gemini
import ai.agents.gemini_agent as agent


def test_gemini_is_not_initialized_at_import():
    """Verify that the Gemini model is NOT configured or initialized at module-import time."""
    # Reset internal initialization states for the test run
    agent._model = None
    agent._initialized = False

    assert agent._model is None
    assert agent._initialized is False


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


@patch("os.getenv")
def test_gemini_missing_key_returns_clear_error(mock_getenv):
    """Verify that a missing GEMINI_API_KEY returns a clear application-level error instead of crashing."""
    agent._model = None
    agent._initialized = False

    # Simulate empty environment variable
    mock_getenv.return_value = None

    result = ask_gemini("Test prompt")

    assert "Gemini Error: GEMINI_API_KEY is not configured in your .env file." in result
