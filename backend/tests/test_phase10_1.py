# backend/tests/test_phase10_1.py
import pytest
import asyncio
import datetime
import sqlite3
from unittest.mock import MagicMock, patch

from core.agent.agent_runtime import agent_runtime
from core.agent.goal_manager import goal_manager
from core.agent.policy_engine import policy_engine
from core.context.memory_manager import memory_manager
from core.context.long_term_goals import goal_manager_9b
from core.context.self_model import self_model
from core.context.world_model import world_model


@pytest.fixture(autouse=True)
def clean_continuous_loop_states():
    """Wipes active goal databases and ensures continuous loop tasks are stopped and isolated."""
    # Ensure background loop is fully stopped before and after test
    agent_runtime.stop_continuous_loop()
    agent_runtime.cycle_count = 0
    agent_runtime.state = "IDLE"

    memory_manager.clear_all_context_memory()

    # Clean the Long Term Goals database explicitly
    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()

    yield

    agent_runtime.stop_continuous_loop()
    agent_runtime.cycle_count = 0
    agent_runtime.state = "IDLE"
    memory_manager.clear_all_context_memory()

    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()


@pytest.mark.anyio
async def test_coordinator_boot_and_duplicate_start_prevention():
    """Verify that the continuous loop starts and statefully prevents duplicate runners."""
    assert agent_runtime.continuous_running is False

    # 1. Start the loop
    success_1 = agent_runtime.start_continuous_loop()
    assert success_1 is True
    assert agent_runtime.continuous_running is True

    # 2. Try starting concurrently (duplicate block)
    success_2 = agent_runtime.start_continuous_loop()
    assert success_2 is False

    # 3. Graceful shutdown
    agent_runtime.stop_continuous_loop()
    assert agent_runtime.continuous_running is False
    assert agent_runtime.state == "IDLE"


@pytest.mark.anyio
async def test_23_step_lifecycle_ordering_and_cycle_count():
    """Verify that the continuous runner ticks statefully, loads goals, and increments cycles."""
    # Seed a persistent long-term goal
    goal_manager_9b.create_goal(
        goal_id="lt_goal_001",
        description="Check time continuously",
        priority="LOW"
    )

    # Start loop in background
    agent_runtime.loop_interval_sec = 0.05
    agent_runtime.start_continuous_loop()

    # Await slightly to let the background thread tick at least 2 cycles
    await asyncio.sleep(0.20)

    # Stop and assert
    agent_runtime.stop_continuous_loop()
    assert agent_runtime.cycle_count >= 2

    # Verify that the goal status was processed and updated statefully in SQLite
    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM long_term_goals WHERE goal_id = 'lt_goal_001'")
    status_row = cursor.fetchone()
    assert status_row["status"] == "COMPLETED"
    conn.close()


@pytest.mark.anyio
async def test_policy_budget_lockout_in_continuous_loop():
    """Verify that the continuous coordinator respects policy budget caps and halts safely on breach."""
    # Exceed policy budget pre-flight
    policy_engine.tool_calls_count = 15 # Hard limit is 10

    # Seed a persistent long-term goal
    goal_manager_9b.create_goal(
        goal_id="lt_goal_budget",
        description="Diagnostics task",
        priority="LOW"
    )

    agent_runtime.loop_interval_sec = 0.01
    agent_runtime.start_continuous_loop()

    # Wait for loop to evaluate
    await asyncio.sleep(0.05)

    # The coordinator should detect the budget breach in Step 13, halt execution, and set state to BLOCKED
    assert agent_runtime.state == "BLOCKED"
    agent_runtime.stop_continuous_loop()
    policy_engine.reset_counters()


@pytest.mark.anyio
async def test_failure_fallback_to_safe_phase_9a():
    """Verify that any unhandled exception in the background thread halts the task safely and resets to IDLE fallback."""
    agent_runtime.loop_interval_sec = 0.01
    agent_runtime.start_continuous_loop()

    # Mock long-term goal retrieval to raise an OperationalError, simulating a database crash/exception
    with patch.object(goal_manager_9b, "get_active_goals_with_subgoals", side_effect=sqlite3.OperationalError("Mock crash")):
        await asyncio.sleep(0.05)

        # Background task should capture the error, log the fallback, and reset status safely to IDLE
        assert agent_runtime.continuous_running is False
        assert agent_runtime.state == "IDLE"


@pytest.mark.anyio
async def test_resource_budget_high_cpu_throttling():
    """Verify that the self-model CPU scanner blocks cycle execution under high-CPU stress loads."""
    # Mock self-model resource state to return high CPU usage
    mock_resource = {
        "cpu_percent": 99.0, # Stress load threshold (>95%)
        "ram_used_mb": 400.0,
        "ram_total_mb": 16000.0,
        "gpu_vram_used_mb": 0.0,
        "gpu_vram_total_mb": 4096.0
    }

    # Seed a persistent long-term goal
    goal_manager_9b.create_goal(
        goal_id="lt_goal_cpu",
        description="Heavy computations",
        priority="LOW"
    )

    with patch.object(self_model, "get_resource_state", return_value=mock_resource):
        agent_runtime.loop_interval_sec = 0.01
        agent_runtime.start_continuous_loop()

        await asyncio.sleep(0.05)

        # Since CPU is >95%, Step 2 blocks cycle execution, keeping cycle count to 1 (initial boot/start check)
        assert agent_runtime.cycle_count == 1
        agent_runtime.stop_continuous_loop()


@pytest.mark.anyio
async def test_phase_9a_direct_fallback_execution():
    """Verify that direct synchronous/asynchronous execute_goal remains fully supported as a fallback."""
    goal_desc = "prepare system and check time"

    with patch("core.agent.tool_orchestrator.tool_orchestrator.execute_action", return_value="success"):
        success, msg = await agent_runtime.execute_goal(goal_desc)
        assert success is True
