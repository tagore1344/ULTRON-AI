from ai_router import ask_ai


def test_router_smoke():
    answer = ask_ai("Say hello in one short sentence.", provider="gemini")
    assert isinstance(answer, str)
    assert answer