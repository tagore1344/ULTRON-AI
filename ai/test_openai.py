from openai_client import ask_openai


def test_openai_smoke():
    answer = ask_openai("Say hello in one short sentence.")
    assert isinstance(answer, str)
    assert answer