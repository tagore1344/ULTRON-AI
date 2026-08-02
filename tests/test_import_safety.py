import importlib


def test_manual_ai_scripts_are_import_safe():
    for module_name in [
        "ai.test_deepseek",
        "ai.test_gemini",
        "ai.test_openai",
        "ai.test_orchestrator",
        "ai.test_router",
    ]:
        importlib.import_module(module_name)


def test_ai_router_unknown_provider():
    from ai.ai_router import ask_ai

    assert ask_ai("hello", provider="unknown") == "Unknown AI Provider"
