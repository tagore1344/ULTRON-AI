from deepseek_client import ask_deepseek


def test_deepseek_smoke():
    answer = ask_deepseek("Say hello in one short sentence.")
    assert isinstance(answer, str)
    assert answer
