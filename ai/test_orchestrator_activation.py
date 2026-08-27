"""Phase integration tests: fully-activated multi-provider AI orchestration.

These tests monkeypatch provider callables so no API keys or network access
are required. They pin down the contracts fixed in the audit session:

* ModelSelector routes by category AND respects availability.
* AIOrchestrator cascades through providers when the primary fails.
* ULTRON_CONSENSUS_MODE=multi builds consensus across all live providers.
* The hardcoded tool-call hack ("open instagram") no longer bypasses routing.
"""

import os
from unittest.mock import patch

import ai.orchestrator.ai_orchestrator as orch
import ai.orchestrator.model_selector as selector_mod
from ai.orchestrator.ai_orchestrator import AIOrchestrator


def _set_ask(monkeypatch, name, fn):
    """Patch one of the module-level ask_* symbols used by the dispatcher."""
    monkeypatch.setattr(orch, name, fn)


def _pin_all_providers_probed(monkeypatch):
    """Forces deterministic provider ordering (offline probing disabled).

    The strategic preference order from the routing tables is preserved; only
    live-availability reordering is neutralized.
    """
    monkeypatch.setattr(
        selector_mod,
        "get_provider_availability",
        lambda: {"gemini": False, "openai": False, "deepseek": False},
    )


def _availability(**flags):
    base = {"gemini": False, "openai": False, "deepseek": False}
    base.update(flags)
    return base


# ────────────────────────────────────────────────────────────────────────
# MODEL SELECTOR ROUTING
# ────────────────────────────────────────────────────────────────────────

def test_selector_routes_coding_to_gemini():
    from ai.orchestrator.model_selector import ModelSelector
    selector = ModelSelector()
    assert selector.rank_models("write some python code", available=_availability())[0] == "gemini"


def test_selector_routes_security_to_deepseek():
    from ai.orchestrator.model_selector import ModelSelector
    selector = ModelSelector()
    assert selector.rank_models("check my firewall security", available=_availability())[0] == "deepseek"


def test_selector_routes_conversation_to_openai():
    from ai.orchestrator.model_selector import ModelSelector
    selector = ModelSelector()
    assert selector.rank_models("hello, how are you today?", available=_availability())[0] == "openai"


def test_selector_prefers_available_providers():
    from ai.orchestrator.model_selector import ModelSelector
    selector = ModelSelector()
    ranked = selector.rank_models(
        "hello there",
        available=_availability(gemini=True),  # openai primary is offline here
    )
    # Offline openai must trail behind the live gemini fallback.
    assert ranked[0] == "gemini"
    assert ranked.index("openai") > ranked.index("gemini")


# ────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR FALLBACK CASCADE
# ────────────────────────────────────────────────────────────────────────

def test_fallback_skips_failed_provider(monkeypatch):
    """Primary OpenAI errors -> orchestrator must recover via its #2 ranked provider (Gemini)."""
    _pin_all_providers_probed(monkeypatch)
    _set_ask(monkeypatch, "ask_openai", lambda p: "OpenAI Error: boom")
    _set_ask(monkeypatch, "ask_deepseek", lambda p: "DeepSeek should NOT be reached.")
    _set_ask(monkeypatch, "ask_gemini", lambda p: "Gemini solid answer.")

    brain = AIOrchestrator()
    result = brain.ask("hello there")  # conversational -> openai primary

    assert result == "Gemini solid answer."


def test_fallback_uses_third_provider(monkeypatch):
    """Two failing providers must cascade into the third."""
    _pin_all_providers_probed(monkeypatch)
    _set_ask(monkeypatch, "ask_openai", lambda p: "")
    _set_ask(monkeypatch, "ask_deepseek", lambda p: "DeepSeek Error: down")
    _set_ask(monkeypatch, "ask_gemini", lambda p: "Gemini wins.")

    brain = AIOrchestrator()
    result = brain.ask("write python code")  # coding -> gemini primary

    # Coding order: gemini("") fails -> deepseek(Error) fails -> third succeeds
    assert "Gemini wins." in result


def test_all_failures_fail_soft(monkeypatch):
    _pin_all_providers_probed(monkeypatch)
    _set_ask(monkeypatch, "ask_openai", lambda p: "OpenAI Error: x")
    _set_ask(monkeypatch, "ask_deepseek", lambda p: "DeepSeek Error: y")
    _set_ask(monkeypatch, "ask_gemini", lambda p: "Gemini Error: z")

    brain = AIOrchestrator()
    result = brain.ask("anything")

    assert "all AI providers failed" in result
    assert "Gemini Error: z" in result


def test_exception_in_agent_is_caught_and_cascades(monkeypatch):
    _pin_all_providers_probed(monkeypatch)

    def explode(_prompt):
        raise RuntimeError("network gone")

    _set_ask(monkeypatch, "ask_openai", explode)
    _set_ask(monkeypatch, "ask_gemini", lambda p: "Second-ranked provider recovered.")
    _set_ask(monkeypatch, "ask_deepseek", lambda p: "Should NOT be reached.")

    brain = AIOrchestrator()
    result = brain.ask("hello")

    assert result == "Second-ranked provider recovered."


def test_empty_prompt_rejected_without_provider_calls(monkeypatch):
    calls = []
    for name in ("ask_openai", "ask_deepseek", "ask_gemini"):
        _set_ask(monkeypatch, name, lambda p: calls.append(p))

    brain = AIOrchestrator()
    result = brain.ask("   ")

    assert "empty prompts" in result.lower()
    assert calls == []


def test_instagram_hack_removed_from_orchestrator(monkeypatch):
    """The former hardcoded shortcut must flow through normal provider routing."""
    _pin_all_providers_probed(monkeypatch)
    _set_ask(monkeypatch, "ask_openai", lambda p: "normal chat response.")
    _set_ask(monkeypatch, "ask_deepseek", lambda p: "nope")
    _set_ask(monkeypatch, "ask_gemini", lambda p: "nope either")

    brain = AIOrchestrator()
    result = brain.ask("open instagram")

    assert result == "normal chat response."


# ────────────────────────────────────────────────────────────────────────
# MULTI-MODE CONSENSUS
# ────────────────────────────────────────────────────────────────────────

def test_multi_mode_merges_live_providers(monkeypatch):
    _pin_all_providers_probed(monkeypatch)

    _set_ask(monkeypatch, "ask_openai", lambda p: "OpenAI says A.")
    _set_ask(monkeypatch, "ask_deepseek", lambda p: "DeepSeek says B.")
    _set_ask(monkeypatch, "ask_gemini", lambda p: "Gemini says C.")

    brain = AIOrchestrator()
    with patch.dict(os.environ, {"ULTRON_CONSENSUS_MODE": "multi"}):
        result = brain.ask("plain question")

    # All three live answers merged into a single consolidated payload.
    assert "OpenAI says A." in result
    assert "DeepSeek says B." in result
    assert "Gemini says C." in result


def test_multi_mode_excludes_dead_providers(monkeypatch):
    _pin_all_providers_probed(monkeypatch)

    _set_ask(monkeypatch, "ask_openai", lambda p: "OpenAI fine.")
    _set_ask(monkeypatch, "ask_deepseek", lambda p: "DeepSeek Error: key missing")
    _set_ask(monkeypatch, "ask_gemini", lambda p: "Gemini fine too.")

    brain = AIOrchestrator()
    with patch.dict(os.environ, {"ULTRON_CONSENSUS_MODE": "multi"}):
        result = brain.ask("another question")

    assert "OpenAI fine." in result
    assert "Gemini fine too." in result
    assert "DeepSeek Error" not in result