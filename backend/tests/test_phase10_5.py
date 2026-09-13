# backend/tests/test_phase10_5.py
import pytest
import sqlite3
import datetime
import asyncio
from unittest.mock import MagicMock, patch

from core.agent.meta_reasoning import meta_reasoning_engine, MetaReasoningRecord
from core.context.memory_manager import memory_manager
from core.context.long_term_goals import goal_manager_9b
from core.neural.neural_memory import neural_memory
from core.agent.agent_runtime import agent_runtime


@pytest.fixture(autouse=True)
def clean_meta_reasoning_states():
    """Wipes active records, context databases, and runs cleanup between tests."""
    meta_reasoning_engine.records.clear()
    meta_reasoning_engine.calibration_error_history.clear()
    meta_reasoning_engine.reflection_depth = 0

    memory_manager.clear_all_context_memory()

    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()

    conn_neural = neural_memory.get_connection()
    cursor_neural = conn_neural.cursor()
    cursor_neural.execute("DELETE FROM neural_edges")
    cursor_neural.execute("DELETE FROM neural_nodes")
    conn_neural.commit()
    conn_neural.close()

    yield

    meta_reasoning_engine.records.clear()
    meta_reasoning_engine.calibration_error_history.clear()
    meta_reasoning_engine.reflection_depth = 0

    memory_manager.clear_all_context_memory()

    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()


def test_prediction_discrepancy_and_evaluation_calibration():
    """Verify that the engine calculates prediction-vs-observation discrepancy and calibration scores correctly."""
    record = MetaReasoningRecord(
        cycle_id="cycle_01",
        goal="Check local diagnostics",
        predicted_success=0.95,
        actual_success=True,
        predicted_latency=0.20,
        actual_latency=0.35, # 0.15 discrepancy
        predicted_tokens=500,
        actual_tokens=1500 # 1000 discrepancy
    )

    # 1. Assert discrepancy calculations
    assert record.get_latency_discrepancy() == pytest.approx(0.15)
    assert record.get_token_discrepancy() == 1000

    # 2. Assert calibration evaluation
    calibration = meta_reasoning_engine.evaluate_cycle_calibration(record)
    assert calibration["combined_calibration_error"] >= 0.0
    assert len(meta_reasoning_engine.calibration_error_history) == 1


def test_plan_quality_scoring():
    """Verify plan quality scoring decreases on high retries and latency overheads."""
    r1 = MetaReasoningRecord("c1", "task", 0.95, True, 0.20, 0.22, 500, 500)
    eval_perfect = meta_reasoning_engine.evaluate_plan_quality(r1, retries=0)
    assert eval_perfect["plan_quality_score"] == 100.0 # Perfect execution

    r2 = MetaReasoningRecord("c2", "task", 0.95, True, 0.20, 1.5, 500, 500) # High latency overhead & retries
    eval_poor = meta_reasoning_engine.evaluate_plan_quality(r2, retries=2)
    # Score should be penalised
    assert eval_poor["plan_quality_score"] < 100.0


def test_judgment_quality_scoring_and_false_disagreement():
    """Verify judgment quality scoring and false-disagreement flags are compiled correctly."""
    # High confidence (0.95) matches successful outcome -> high quality
    eval_good = meta_reasoning_engine.evaluate_judgment_quality(opinion_confidence=0.95, observed_success=True)
    assert eval_good["judgment_quality_score"] >= 90.0
    assert eval_good["is_false_disagreement"] is False

    # Low confidence (0.10) with successful outcome -> false-disagreement triggered
    eval_bad = meta_reasoning_engine.evaluate_judgment_quality(opinion_confidence=0.10, observed_success=True)
    assert eval_bad["judgment_quality_score"] < 50.0
    assert eval_bad["is_false_disagreement"] is True


def test_self_questioning_and_recursion_depth_budget_locks():
    """Verify self-questioning limits recursion depth, token allocations, and execution runtimes securely."""
    # 1. Successful reflection run
    res = meta_reasoning_engine.reflect_self_questioning("Why did I choose this plan?")
    assert "expected success" in res["verdict"]

    # 2. Exceed recursion depth cap (max 3)
    meta_reasoning_engine.reflection_depth = 4
    with pytest.raises(RecursionError, match="recursion limit exceeded"):
        meta_reasoning_engine.reflect_self_questioning("Why did I choose this plan?")

    meta_reasoning_engine.reflection_depth = 0 # reset

    # 3. Exceed token budget limit (max 1000)
    with pytest.raises(ValueError, match="token budget requested"):
        meta_reasoning_engine.reflect_self_questioning("Why did I choose this plan?", tokens_allocated=1500)

    # 4. Exceed runtime timeout limit (max 5s)
    # Stateful lambda to increase time on each call, instantly triggering timeout
    time_val = [0.0]
    def mock_time():
        time_val[0] += 10.0
        return time_val[0]

    with patch("time.time", side_effect=mock_time):
        with pytest.raises(TimeoutError, match="runtime limit"):
            meta_reasoning_engine.reflect_self_questioning("Why did I choose this plan?")


@pytest.mark.anyio
async def test_regression_preservation_and_lessons_persistence():
    """Verify pre-existing continuous loops and plan dispatches run green with the integrated meta-reasoning layer."""
    goal_desc = "prepare system and check time"
    with patch("core.agent.tool_orchestrator.tool_orchestrator.execute_action", return_value="success"):
        success, msg = await agent_runtime.execute_goal(goal_desc)
        assert success is True
        assert len(meta_reasoning_engine.records) >= 1
        assert meta_reasoning_engine.records[0].goal == goal_desc
