"""OpenAI provider adapter for ULTRON."""
from __future__ import annotations

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
if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
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
    """Ask the configured OpenAI model using the modern Responses API."""
    if client is None:
        return "OpenAI Error: API dependency or OPENAI_API_KEY is unavailable."

    try:
        response = client.responses.create(
            model=os.getenv("ULTRON_MODEL", "gpt-6-astra"),
            reasoning={"effort": os.getenv("ULTRON_REASONING_EFFORT", "high")},
            instructions="You are ULTRON AI, an advanced, precise, tool-aware assistant.",
            input=prompt,
        )
        return response.output_text
    except Exception as exc:
        return f"OpenAI Error: {exc}"
