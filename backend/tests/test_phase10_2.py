# backend/tests/test_phase10_2.py
import pytest
import sqlite3
import datetime
import json
import asyncio
from unittest.mock import MagicMock, patch

from core.context.memory_manager import memory_manager
from core.context.memory_consolidator import memory_consolidator
from core.context.self_model import self_model
from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralNodeModel
from core.agent.agent_runtime import agent_runtime


@pytest.fixture(autouse=True)
def clean_memory_and_neural_tables():
    """Wipes context episodic and neural tables to guarantee total isolation."""
    memory_manager.clear_all_context_memory()

    conn = neural_memory.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM neural_edges")
    cursor.execute("DELETE FROM neural_nodes")
    conn.commit()
    conn.close()

    yield

    memory_manager.clear_all_context_memory()
    conn = neural_memory.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM neural_edges")
    cursor.execute("DELETE FROM neural_nodes")
    conn.commit()
    conn.close()


def test_importance_score_calculation():
    """Verify that the consolidator calculates correct importance scores using the success/latency/rarity formula."""
    # 1. High-value failure with high latency (should score >= 8.0)
    failed_ep = {
        "success_status": False,
        "resource_latency_sec": 1.9,
        "parsed_intent": "composite_task"
    }
    score_fail = memory_consolidator.calculate_importance_score(failed_ep)
    assert score_fail >= 8.0

    # 2. Low-value simple success (should score < 8.0)
    success_ep = {
        "success_status": True,
        "resource_latency_sec": 0.05,
        "parsed_intent": "system.time"
    }
    score_succ = memory_consolidator.calculate_importance_score(success_ep)
    assert score_succ < 8.0


def test_promotion_from_episodic_to_semantic_and_neural_schema():
    """Verify that high-value episodes (score >= 8.0) promote to Semantic memory and create Concept nodes in the Neural Schema."""
    # Seed high-value episode directly in episodic table
    memory_manager.add_episodic_memory(
        user_prompt="Run deep audit with password='123'",
        parsed_intent="composite_system_audit",
        actual_results="critical failures detected",
        success_status=False,
        resource_latency_sec=2.1
    )

    # Initially, no concepts exist in neural schema
    assert neural_memory.get_node("concept_composite_system_audit") is None

    # Run consolidation sweep
    success = memory_consolidator.run_consolidation_sweep()
    assert success is True

    # Assert new Concept node was created statefully
    node = neural_memory.get_node("concept_composite_system_audit")
    assert node is not None
    assert node.node_type == "CONCEPT"
    # Verify privacy sanitization occurred (the password in the prompt must be redacted!)
    assert "password=<REDACTED>" in node.properties["last_prompt"]
    assert "123" not in node.properties["last_prompt"]


def test_confidence_decay_safety():
    """Verify that unverified semantic concepts decay confidence, but known verified facts are completely preserved."""
    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

    # 1. Save Unverified Node (B = 0.50)
    unverified_node = NeuralNodeModel(
        node_id="concept_unverified",
        node_type="CONCEPT",
        label="Unverified concept",
        properties={},
        belief_confidence=0.50,
        operational_state="UNVERIFIED",
        last_updated=now_str
    )
    neural_memory.save_node(unverified_node)

    # 2. Save Known/Verified Node (B = 0.95)
    known_node = NeuralNodeModel(
        node_id="concept_known",
        node_type="CONCEPT",
        label="Known factual concept",
        properties={},
        belief_confidence=0.95,
        operational_state="KNOWN",
        last_updated=now_str
    )
    neural_memory.save_node(known_node)

    # Run confidence decay
    memory_consolidator.apply_confidence_decay()

    # Assert unverified decays by 5% (0.50 * 0.95 = 0.475)
    decayed_node = neural_memory.get_node("concept_unverified")
    assert decayed_node.belief_confidence == 0.475

    # Assert known verified factual node remains preserved at 0.95!
    preserved_node = neural_memory.get_node("concept_known")
    assert preserved_node.belief_confidence == 0.95


def test_contradiction_handling_during_consolidation():
    """Verify that the consolidator detects contradictions and resolves them via factual overrides."""
    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

    # Seed a high confidence belief that connection is KNOWN success
    node = NeuralNodeModel(
        node_id="concept_composite_wifi_check",
        node_type="CONCEPT",
        label="WiFi checks",
        properties={},
        belief_confidence=0.95,
        operational_state="KNOWN",
        last_updated=now_str
    )
    neural_memory.save_node(node)

    # Seed a high-value episodic failure (contradiction!)
    memory_manager.add_episodic_memory(
        user_prompt="Run WiFi tests",
        parsed_intent="composite_wifi_check",
        actual_results="network disconnected",
        success_status=False, # Fails!
        resource_latency_sec=1.8
    )

    # Run sweep
    memory_consolidator.run_consolidation_sweep()

    # Subjective belief should be overridden by the hard episodic failure fact
    updated_node = neural_memory.get_node("concept_composite_wifi_check")
    assert updated_node.belief_confidence < 0.35
    assert updated_node.operational_state == "FAILED"


def test_consolidation_resource_budget_high_cpu_throttling():
    """Verify that the consolidator aborts and bypasses sweeps under high CPU stress loads."""
    mock_resource = {
        "cpu_percent": 95.0, # Stress limit >90%
        "ram_used_mb": 400.0,
        "ram_total_mb": 16000.0,
        "gpu_vram_used_mb": 0.0,
        "gpu_vram_total_mb": 4096.0
    }

    with patch.object(self_model, "get_resource_state", return_value=mock_resource):
        success = memory_consolidator.run_consolidation_sweep()
        assert success is False # Aborted/Throttled cleanly


def test_consolidation_db_failure_recovery():
    """Verify the consolidator rolls back and fails safely on database query crashes without throwing uncaught exceptions."""
    with patch.object(memory_manager, "get_connection", side_effect=sqlite3.OperationalError("Database crashed")):
        try:
            success = memory_consolidator.run_consolidation_sweep()
            assert success is False # Failed safely
            error_thrown = False
        except Exception:
            error_thrown = True

        assert error_thrown is False # No uncaught exceptions thrown!


@pytest.mark.anyio
async def test_phase_10_1_regression_preservation():
    """Verify that the continuous loop runs cleanly and incorporates the memory consolidator sweep without regressions."""
    agent_runtime.loop_interval_sec = 0.01
    agent_runtime.start_continuous_loop()

    # Let the loop runner tick
    await asyncio.sleep(0.05)

    agent_runtime.stop_continuous_loop()
    assert agent_runtime.cycle_count >= 1
