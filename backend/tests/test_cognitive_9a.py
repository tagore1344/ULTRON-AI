# backend/tests/test_cognitive_9a.py
import pytest
import asyncio
from unittest.mock import MagicMock, patch

from core.agent.judgment_engine import judgment_engine, Opinion
from core.agent.agent_runtime import agent_runtime
from core.agent.planner import planner, CandidatePlan
from core.agent.goal_manager import goal_manager
from core.agent.policy_engine import policy_engine
from core.agent.tool_orchestrator import tool_orchestrator
from core.tools.tool_registry import ToolRegistry


@pytest.fixture(autouse=True)
def clean_agent_cognitive_states():
    """Reset cognitive runtime and policy engine between runs to avoid pollution."""
    agent_runtime.state = "IDLE"
    agent_runtime.active_goal_id = None
    agent_runtime.latest_opinion = None
    agent_runtime.latest_self_evaluation = None
    goal_manager.clear_goal()

    policy_engine.reset_counters()
    policy_engine.set_autonomy(3)
    policy_engine.max_tool_calls = 10
    policy_engine.token_budget = 10000
    yield
    goal_manager.clear_goal()
    policy_engine.reset_counters()


def test_structured_opinion_creation():
    """Verify that an Opinion can be created with all necessary structural sections."""
    opinion = Opinion(
        conclusion="Optimized route chosen.",
        facts=["Fact 1", "Fact 2"],
        inferences=["Inference 1"],
        hypotheses=["Hypothesis 1"],
        preferences=["Preference 1"],
        uncertainties=["Uncertainty 1"],
        confidence_score=0.85,
        evidence=["Evidence 1"],
        assumptions=["Assumption 1"],
        alternatives=["Alternative 1"],
        downside_risks=["Risk 1"],
        tradeoffs=["Tradeoff 1"],
        recommended_action="Execute fallback.",
        is_disagreement=False
    )

    assert opinion.conclusion == "Optimized route chosen."
    assert "Fact 1" in opinion.facts
    assert "Inference 1" in opinion.inferences
    assert "Hypothesis 1" in opinion.hypotheses
    assert "Preference 1" in opinion.preferences
    assert "Uncertainty 1" in opinion.uncertainties
    assert opinion.confidence_score == 0.85
    assert opinion.is_disagreement is False

    d = opinion.to_dict()
    assert d["conclusion"] == "Optimized route chosen."
    assert d["confidence_score"] == 0.85


def test_fact_inference_hypothesis_separation_in_engine():
    """Verify that the JudgmentEngine separates and compiles real cognitive sections."""
    opinion = judgment_engine.generate_opinion("Should I use tiny.en or base.en for ULTRON?")

    assert opinion is not None
    assert len(opinion.facts) >= 2
    assert len(opinion.inferences) >= 1
    assert len(opinion.hypotheses) >= 1
    assert len(opinion.preferences) >= 1
    assert len(opinion.uncertainties) >= 1
    assert 0.0 <= opinion.confidence_score <= 1.0
    assert len(opinion.evidence) >= 1
    assert len(opinion.assumptions) >= 1
    assert len(opinion.alternatives) >= 1
    assert len(opinion.downside_risks) >= 1
    assert len(opinion.tradeoffs) >= 1
    assert len(opinion.recommended_action) > 0


def test_disagreement_detection_tiny_en():
    """Verify the Interactive Disagreement Protocol triggers on suboptimal tiny.en claims."""
    # "tiny.en is better" is a suboptimal user strategy
    opinion = judgment_engine.generate_opinion("tiny.en is better than base.en")
    assert opinion.is_disagreement is True
    assert opinion.disagreement_justification is not None
    assert "suboptimal" in opinion.disagreement_justification.lower()


@pytest.mark.anyio
async def test_disagreement_halts_loop_with_feedback():
    """Verify the cognitive loop aborts and reports disagreement without running plans."""
    with patch.object(planner, "generate_plan") as mock_plan:
        success, msg = await agent_runtime.execute_goal("tiny.en is better than base.en")

        assert success is False
        assert "DISAGREEMENT" in msg
        assert "suboptimal" in msg.lower()
        mock_plan.assert_not_called()


def test_alternative_plan_generation():
    """Verify that the Planner generates multiple candidate plans for complex requests."""
    candidates = planner.generate_candidates("prepare system and check time")

    assert len(candidates) >= 2
    c1 = candidates[0]
    c2 = candidates[1]

    assert c1.name == "serial_diagnostic_time"
    assert c1.expected_success == 0.98
    assert "system.info" in c1.required_tools

    assert c2.name == "direct_time_check"
    assert c2.expected_success == 0.95
    assert "system.time" in c2.required_tools


def test_best_plan_selection():
    """Verify that the Planner correctly evaluates and selects the optimal candidate plan."""
    # When multiple plans are present, planner.generate_plan returns the graph of the best one
    graph = planner.generate_plan("prepare system and check time")
    assert graph is not None
    # Best candidate is "serial_diagnostic_time" with success 0.98
    assert "node_001" in graph.nodes
    assert graph.nodes["node_001"].intent == "system.info"


@pytest.mark.anyio
async def test_predicted_vs_actual_self_evaluation():
    """Verify the continuous self-evaluation registers predicted vs actual metrics after run."""
    goal_desc = "prepare system and check time"

    with patch.object(tool_orchestrator, "execute_action", return_value="success"):
        success, msg = await agent_runtime.execute_goal(goal_desc)

        assert success is True
        evaluation = agent_runtime.get_self_evaluation()
        assert evaluation is not None
        assert evaluation["goal"] == goal_desc
        assert evaluation["success"] is True
        assert evaluation["elapsed_seconds"] >= 0.0
        assert evaluation["tool_calls_spent"] == 2
        assert evaluation["tokens_spent"] == 1000
        assert "lessons_learned" in evaluation


@pytest.mark.anyio
async def test_tool_registry_diagnostics():
    """Verify cognitive diagnostic tools are accessible via the ToolRegistry."""
    registry = ToolRegistry()

    # 1. Test get_opinion when none exists
    res_no_opinion = await registry.execute({"intent": "agent.get_opinion"})
    assert "No opinion" in res_no_opinion

    # 2. Trigger a goal to generate an opinion
    with patch.object(tool_orchestrator, "execute_action", return_value="success"):
        await agent_runtime.execute_goal("Should I use tiny.en or base.en for ULTRON?")

    # 3. Test get_opinion now returns serialized opinion
    res_opinion = await registry.execute({"intent": "agent.get_opinion"})
    assert "base.en" in res_opinion

    # 4. Test get_self_evaluation returns evaluation dict
    res_eval = await registry.execute({"intent": "agent.get_self_evaluation"})
    assert "elapsed_seconds" in res_eval


@pytest.mark.anyio
async def test_security_boundary_and_high_risk_protection():
    """Verify that HIGH_RISK intents fail closed in the cognitive core runtime."""
    # "shutdown" generates a candidate, but the policy engine blocks the execution
    success, msg = await agent_runtime.execute_goal("shutdown")
    assert success is False
    assert "blocked" in msg.lower() or "failure" in msg.lower()
