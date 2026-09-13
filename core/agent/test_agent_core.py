from core.agent.agent_loop import AgentLoop
from core.agent.planner import TaskPlanner
from core.agent.task_state import TaskState
from core.agent.verifier import Verifier


def test_planner_creates_verifiable_coding_steps():
    steps = TaskPlanner().plan("debug my Python project")
    assert len(steps) >= 4
    assert any("tests" in step.lower() for step in steps)


def test_task_state_is_serialisable():
    state = TaskState("test goal")
    state.record_action("x", {"a": 1})
    state.record_result("ok")
    data = state.to_dict()
    assert data["goal"] == "test goal"
    assert data["actions"][0]["name"] == "x"


def test_agent_loop_completes_and_verifies():
    loop = AgentLoop(
        executor=lambda step, state: {"step": step},
        verifier=Verifier([lambda value: "step" in value]),
    )
    result = loop.run("create a project")
    assert result.success is True
    assert result.state.status == "completed"
