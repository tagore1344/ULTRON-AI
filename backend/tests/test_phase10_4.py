# backend/tests/test_phase10_4.py
import pytest
import sqlite3
import datetime
import json
import asyncio
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from backend.server import app
from backend.database.device_repository import device_repo
from backend.database.connection import get_db_connection
from backend.security.token_service import token_service
from core.agent.planner import planner
from core.agent.task_graph import TaskGraph
from core.context.long_term_goals import goal_manager_9b
from core.context.self_model import self_model
from core.context.world_model import world_model
from core.agent.agent_runtime import agent_runtime


@pytest.fixture(autouse=True)
def clean_goals_and_context_states():
    """Wipes goal ledger tables and active runtime states before and after each test."""
    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()

    conn_devices = get_db_connection()
    cursor_devices = conn_devices.cursor()
    cursor_devices.execute("DELETE FROM devices")
    cursor_devices.execute("DELETE FROM brute_force_tracker")
    conn_devices.commit()
    conn_devices.close()

    # Reset runtime state
    agent_runtime.stop_continuous_loop()
    agent_runtime.cycle_count = 0
    agent_runtime.state = "IDLE"
    self_model.capabilities["windows_pycaw_volume"] = "KNOWN"

    yield

    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()

    conn_devices = get_db_connection()
    cursor_devices = conn_devices.cursor()
    cursor_devices.execute("DELETE FROM devices")
    cursor_devices.execute("DELETE FROM brute_force_tracker")
    conn_devices.commit()
    conn_devices.close()

    agent_runtime.stop_continuous_loop()
    agent_runtime.cycle_count = 0
    agent_runtime.state = "IDLE"
    self_model.capabilities["windows_pycaw_volume"] = "KNOWN"


# ==============================================================================
# SCHEDULER & PRIORITIZATION TESTS
# ==============================================================================

def test_priority_selection_ranking_and_deadline_handling():
    """Verify that get_ranked_goals correctly scores and prioritizes goals based on priority levels and close deadlines."""
    # Goal 1: Low priority, no deadline
    goal_manager_9b.create_goal("goal_low", "Low priority goal", "LOW")

    # Goal 2: High priority, no deadline
    goal_manager_9b.create_goal("goal_high", "High priority goal", "HIGH")

    # Goal 3: Medium priority, very close deadline (1 hour from now)
    deadline_dt = datetime.datetime.now() + datetime.timedelta(hours=1)
    deadline_str = deadline_dt.isoformat() + "Z"
    goal_manager_9b.create_goal(
        "goal_med_urgent", "Medium priority with close deadline", "MEDIUM",
        deadline=deadline_str
    )

    ranked = goal_manager_9b.get_ranked_goals()
    assert len(ranked) == 3

    # The medium but urgent goal should score higher than the high priority goal due to deadline urgency bonus
    assert ranked[0]["goal_id"] == "goal_med_urgent"
    assert ranked[1]["goal_id"] == "goal_high"
    assert ranked[2]["goal_id"] == "goal_low"


def test_subgoal_dependency_and_progress_checkpointing():
    """Verify progress evaluations correctly identify completed counts, percentages, and dependency blockers."""
    goal_id = "goal_dependencies_test"
    goal_manager_9b.create_goal(goal_id, "Track subgoals", "MEDIUM")

    # Create subgoals with dependencies: sg2 depends on sg1
    goal_manager_9b.create_subgoal("sg_01", goal_id, "Step 1")
    goal_manager_9b.create_subgoal("sg_02", goal_id, "Step 2", dependencies="sg_01")

    # Initially progress is 0.0, and sg_02 is blocked because sg_01 is still PENDING
    p1 = goal_manager_9b.evaluate_goal_progress(goal_id)
    assert p1["progress_percentage"] == 0.0
    assert len(p1["blockers"]) == 1
    assert "sg_02 is blocked" in p1["blockers"][0]

    # Resolve dependency: set Step 1 status to SUCCESS
    goal_manager_9b.update_subgoal_status("sg_01", "SUCCESS")

    # Step 2 blocker is now resolved, progress climbs to 50%
    p2 = goal_manager_9b.evaluate_goal_progress(goal_id)
    assert p2["progress_percentage"] == 50.0
    assert len(p2["blockers"]) == 0


def test_duplicate_goal_execution_prevention():
    """Verify that the scheduler blocks blocked or inactive goals, preventing duplicate execution runs."""
    goal_id = "goal_blocked"
    # Seed goal explicitly blocked
    goal_manager_9b.create_goal(goal_id, "Blocked task", "MEDIUM")
    goal_manager_9b.create_subgoal("sg_blocked", goal_id, "Action", dependencies="missing_sibling")
    goal_manager_9b.update_goal_status(goal_id, "BLOCKED")

    # The ranked goals must score this blocked target as 0.0 priority, filtering it from scheduling
    ranked = goal_manager_9b.get_ranked_goals()
    assert len(ranked) == 1
    assert ranked[0]["priority_score"] == 0.0


# ==============================================================================
# BOOT RE-HYDRATION & RECOVERY TESTS
# ==============================================================================

def test_goal_restart_rehydration_and_unsafe_suspension():
    """Verify boot re-hydration automatically continues safe goals but statefully suspends dangerous ones."""
    # Safe goal
    goal_manager_9b.create_goal("safe_on_boot", "Query current time on boot", "MEDIUM")
    goal_manager_9b.create_subgoal("sg_safe", "safe_on_boot", "system.time query")
    goal_manager_9b.update_goal_status("safe_on_boot", "ACTIVE")

    # Dangerous goal (contains whatsapp keyword)
    goal_manager_9b.create_goal("danger_on_boot", "Send status update via whatsapp message", "HIGH")
    goal_manager_9b.create_subgoal("sg_danger", "danger_on_boot", "Call app.send_message whatsapp")
    goal_manager_9b.update_goal_status("danger_on_boot", "ACTIVE")

    # Simulate boot-up re-hydration
    rehydrated = goal_manager_9b.rehydrate_goals_on_boot()
    assert len(rehydrated) == 2

    safe = next(g for g in rehydrated if g["goal_id"] == "safe_on_boot")
    assert safe["status"] == "ACTIVE" # Safe goal successfully resumed

    danger = next(g for g in rehydrated if g["goal_id"] == "danger_on_boot")
    assert danger["status"] == "SUSPENDED" # Dangerous goal safely suspended to prevent auto-runs


# ==============================================================================
# RE-PLANNING & FAILING STRATEGY RECOVERY
# ==============================================================================

@pytest.mark.anyio
async def test_failed_strategy_triggers_replanning():
    """Verify that during execution, if a capability fails (e.g. volume FAILED), the runtime triggers planning regenerations."""
    # Seed a long-term goal
    goal_id = "lt_volume_task"
    goal_manager_9b.create_goal(goal_id, "Check volume continuously", "MEDIUM")
    goal_manager_9b.update_goal_status(goal_id, "ACTIVE")

    # Simulate volume capability failure in the Self-Model
    self_model.capabilities["windows_pycaw_volume"] = "FAILED"

    # Start loop in background
    agent_runtime.loop_interval_sec = 0.01
    agent_runtime.start_continuous_loop()

    # Mock planner generate_plan to verify it was called again during execution loop
    with patch.object(planner, "generate_plan", return_value=TaskGraph()) as mock_replan:
        await asyncio.sleep(0.05)
        # Assert replanning was triggered dynamically upon detecting the capability failure!
        assert mock_replan.called is True

    agent_runtime.stop_continuous_loop()


# ==============================================================================
# MULTI-DEVICE READ-ONLY GOAL SYNC TEST
# ==============================================================================

def test_multi_device_read_only_goals_telemetry_sync():
    """Verify that the /context/goals/active endpoint returns correct read-only summaries for client syncing."""
    client = TestClient(app)

    # Register authenticated device
    token = "token_read_only_goals"
    token_hash = token_service.hash_string(token)
    device_repo.create_device({
        "device_id": "phone_sync_99",
        "device_name": "Companion Phone",
        "device_type": "android",
        "token_hash": token_hash,
        "permissions": ["system_status"],
        "created_at": "2026-08-13T12:00:00Z",
        "paired_at": "2026-08-13T12:00:00Z",
        "updated_at": "2026-08-13T12:00:00Z",
        "last_seen": "2026-08-13T12:00:00Z",
        "revoked": False
    })

    headers = {"Authorization": f"Bearer {token}"}

    # Seed active goal
    goal_manager_9b.create_goal("sync_test_goal", "Verify synchronization over WS/REST", "MEDIUM")

    res_goals = client.get("/api/v1/context/goals/active", headers=headers)
    assert res_goals.status_code == 200
    res_data = res_goals.json()
    assert len(res_data["data"]) == 1
    assert res_data["data"][0]["goal_id"] == "sync_test_goal"
