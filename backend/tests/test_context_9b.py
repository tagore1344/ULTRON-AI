# backend/tests/test_context_9b.py
import pytest
import os
import datetime
import sqlite3
from unittest.mock import MagicMock, patch

from core.context.memory_manager import memory_manager, sanitize_sensitive_data
from core.context.self_model import self_model
from core.context.world_model import world_model
from core.context.long_term_goals import goal_manager_9b
from core.agent.agent_runtime import agent_runtime
from core.agent.planner import planner
from core.agent.policy_engine import policy_engine
from core.agent.goal_manager import goal_manager
from core.agent.tool_orchestrator import tool_orchestrator
from core.tools.tool_registry import ToolRegistry


@pytest.fixture(autouse=True)
def clean_context_states():
    """Ensure that the context database and self/world models are fully isolated for each test."""
    memory_manager.clear_all_context_memory()
    self_model.failure_locks.clear()
    self_model.confidence_calibration = 0.95
    self_model.autonomy_level = 3

    # Clean the Long Term Goals ledger explicitly
    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()

    yield

    memory_manager.clear_all_context_memory()
    conn = goal_manager_9b.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subgoals")
    cursor.execute("DELETE FROM long_term_goals")
    conn.commit()
    conn.close()


# ==============================================================================
# MEMORY TESTS
# ==============================================================================

def test_memory_persistence_and_partition_isolation():
    """Verify that episodic, semantic, strategy, and failure memories save and remain strictly isolated."""
    # 1. Log Episodic
    ep_id = memory_manager.add_episodic_memory(
        user_prompt="Run system checks",
        parsed_intent="system.info",
        actual_results="system active",
        success_status=True
    )
    assert ep_id.startswith("mem_")

    # 2. Log Semantic
    sem_id = memory_manager.add_semantic_memory(
        category="USER_PREFERENCE",
        keywords="user theme",
        content="Prefer dark obsidian"
    )
    assert sem_id.startswith("know_")

    # 3. Log Strategy
    strat_id = memory_manager.add_strategy_memory(
        task_pattern="Run system checks",
        successful_dag_structure="['node_001']"
    )
    assert strat_id.startswith("strat_")

    # 4. Log Failure
    fail_id = memory_manager.add_failure_memory(
        task_pattern="Run system checks",
        failed_node_intent="system.info",
        error_signature="timeout",
        recovery_decision_applied="FAIL",
        context_snapshot="{}"
    )
    assert fail_id.startswith("fail_")

    # Verify SQL query isolation directly
    conn = memory_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM episodic_memory")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT COUNT(*) FROM semantic_memory")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT COUNT(*) FROM strategy_memory")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT COUNT(*) FROM failure_memory")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_privacy_sanitization_before_storage():
    """Verify that sensitive credentials like Bearer tokens and OpenAI keys are sanitized before storage."""
    raw_prompt = "Login with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and sk-12345678901234567890123456789012 key"
    sanitized = sanitize_sensitive_data(raw_prompt)

    assert "Bearer <REDACTED_TOKEN>" in sanitized
    assert "sk-<REDACTED_OPENAI_KEY>" in sanitized
    assert "eyJhbGciOiJIUzI1NiIsIn" not in sanitized

    # Direct persistence test
    mem_id = memory_manager.add_episodic_memory(
        user_prompt=raw_prompt,
        parsed_intent="auth.login",
        actual_results="password='secret_key_999'",
        success_status=True
    )

    conn = memory_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_prompt, actual_results FROM episodic_memory WHERE memory_id = ?", (mem_id,))
    row = cursor.fetchone()
    assert "sk-<REDACTED_OPENAI_KEY>" in row["user_prompt"]
    assert "password=<REDACTED>" in row["actual_results"]
    conn.close()


def test_memory_multi_criteria_retrieval_ranking():
    """Verify that retrieval searches retrieve matches from partitions sorted by score (relevance+recency+frequency)."""
    # Register strategy memory for "diagnostics check"
    memory_manager.add_strategy_memory(
        task_pattern="diagnostics check",
        successful_dag_structure="['node_1']",
        successful_runs_count=10 # Higher frequency
    )

    # Register semantic memory for "diagnostics check"
    memory_manager.add_semantic_memory(
        category="SYSTEM_DOCS",
        keywords="diagnostics check manual",
        content="Diagnostics check requires active network channels."
    )

    # Search
    results = memory_manager.get_relevant_memories("diagnostics check")
    assert len(results) >= 2
    # Strategy should rank first due to higher relevance weighting and run frequency
    assert results[0]["source_partition"] == "Strategy"
    assert results[1]["source_partition"] == "Semantic"


def test_memory_clear_authorization():
    """Verify that all working and persistent context memories are cleanly reset upon clearing."""
    memory_manager.update_working_memory("temp", "value")
    memory_manager.add_episodic_memory("test", "test", "test", True)

    memory_manager.clear_all_context_memory()
    assert len(memory_manager.working_memory) == 0

    conn = memory_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM episodic_memory")
    assert cursor.fetchone()[0] == 0
    conn.close()


# ==============================================================================
# SELF MODEL TESTS
# ==============================================================================

def test_self_model_state_classification_and_telemetry():
    """Verify self-model tracks autonomy, resource stats, and components mapping KNOWN/UNVERIFIED/UNKNOWN/FAILED."""
    summary = self_model.get_summary()

    assert summary["autonomy_level"] == 3
    assert summary["health_status"] == "HEALTHY"
    assert summary["capabilities"]["local_speech_tts"] == "KNOWN"
    assert summary["capabilities"]["windows_pycaw_volume"] == "UNVERIFIED"
    assert summary["capabilities"]["flutter_sdk_compiler"] == "UNKNOWN"

    assert "cpu_percent" in summary["resources"]
    assert "ram_used_mb" in summary["resources"]


def test_self_model_degradation_on_node_failures():
    """Verify that registering failures degrades self-model confidence calibration and locks components."""
    assert self_model.confidence_calibration == 0.95
    assert len(self_model.failure_locks) == 0

    self_model.register_failure("system.info")
    assert self_model.confidence_calibration < 0.95
    assert "system.info" in self_model.failure_locks


# ==============================================================================
# WORLD MODEL TESTS
# ==============================================================================

def test_world_model_observation_refresh_and_expiration():
    """Verify world model correctly tracks platform processes, networks, and stale expiration thresholds."""
    summary = world_model.get_summary()

    assert summary["operating_system"] is not None
    assert len(summary["network_interfaces"]) >= 1
    assert len(summary["running_processes"]) >= 1
    assert summary["is_stale"] is False

    # Force mock staleness expiration
    world_model.last_updated = datetime.datetime.now() - datetime.timedelta(seconds=150)
    assert world_model.is_stale() is True


# ==============================================================================
# LONG TERM GOAL TESTS
# ==============================================================================

def test_long_term_goal_creation_and_checkpointing():
    """Verify goal manager registers goals, subgoals, checkpoints, and dependencies successfully."""
    goal_id = "goal_9b_test"
    success = goal_manager_9b.create_goal(
        goal_id=goal_id,
        description="Improve speech recognition over 7 days",
        priority="HIGH",
        success_criteria="WER under 5%"
    )
    assert success is True

    # Create subgoals
    sg1 = goal_manager_9b.create_subgoal("sg_001", goal_id, "Gather ambient noise baseline")
    sg2 = goal_manager_9b.create_subgoal("sg_002", goal_id, "Evaluate model accuracy", dependencies="sg_001")
    assert sg1 is True
    assert sg2 is True

    # Verify linkage
    goals = goal_manager_9b.get_active_goals_with_subgoals()
    assert len(goals) == 1
    assert goals[0]["goal_id"] == goal_id
    assert goals[0]["status"] == "PENDING"


def test_long_term_goal_restart_rehydration_and_dangerous_suspension():
    """Verify boot re-hydration is successful and ensures dangerous/external tool goals are SUSPENDED instead of auto-resumed."""
    goal_manager_9b.create_goal("goal_safe", "Check system time on reboot", "MEDIUM")
    goal_manager_9b.create_subgoal("sg_safe", "goal_safe", "Query system.time")
    goal_manager_9b.update_goal_status("goal_safe", "ACTIVE")

    goal_manager_9b.create_goal("goal_dangerous", "Send status update via WhatsApp message", "HIGH")
    goal_manager_9b.create_subgoal("sg_danger", "goal_dangerous", "Call app.send_message to send hello")
    goal_manager_9b.update_goal_status("goal_dangerous", "ACTIVE")

    # Run boot re-hydration
    rehydrated = goal_manager_9b.rehydrate_goals_on_boot()
    assert len(rehydrated) == 2

    # goal_safe is safe to resume
    safe_goal = next(g for g in rehydrated if g["goal_id"] == "goal_safe")
    assert safe_goal["status"] == "ACTIVE"

    # goal_dangerous contains 'whatsapp' / 'send_message' keyword and MUST be suspended safely
    danger_goal = next(g for g in rehydrated if g["goal_id"] == "goal_dangerous")
    assert danger_goal["status"] == "SUSPENDED"


# ==============================================================================
# PHASE 9A INTEGRATIONS & REGRESSIONS
# ==============================================================================

@pytest.mark.anyio
async def test_phase_9a_regression_and_opinion_retrieval():
    """Verify that the Phase 9A cognitive execution loop runs cleanly and saves episodic logs without breaking."""
    goal_desc = "prepare system and check time"

    with patch.object(tool_orchestrator, "execute_action", return_value="success"):
        success, msg = await agent_runtime.execute_goal(goal_desc)

        assert success is True
        # Verify episodic memory was written
        conn = memory_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM episodic_memory")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["user_prompt"] == goal_desc
        assert rows[0]["success_status"] == 1
        conn.close()


@pytest.mark.anyio
async def test_tool_registry_diagnostics_integration():
    """Verify that the ToolRegistry can securely query our newly created Phase 9B contextual models."""
    registry = ToolRegistry()

    # 1. Check self model summary intent
    res_self = await registry.execute({"intent": "agent.get_self_model"})
    assert "capabilities" in res_self
    assert "autonomy_level" in res_self

    # 2. Check world model summary intent
    res_world = await registry.execute({"intent": "agent.get_world_model"})
    assert "operating_system" in res_world
    assert "running_processes" in res_world

    # 3. Check active goals intent
    res_goals = await registry.execute({"intent": "agent.get_active_goals"})
    assert "[]" in res_goals # Initially empty list

    # 4. Check clear memory intent
    res_clear = await registry.execute({"intent": "agent.clear_memory"})
    assert "successfully cleared" in res_clear
