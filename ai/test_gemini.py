from gemini_client import ask_gemini


def test_gemini_smoke():
    answer = ask_gemini("Say hello in one short sentence.")
    assert isinstance(answer, str)
    assert answer