from ai.orchestrator.ai_orchestrator import AIOrchestrator


def test_orchestrator_smoke():
    brain = AIOrchestrator()
    answer = brain.ask("Say hello in one short sentence.")
    assert isinstance(answer, str)
    assert answer