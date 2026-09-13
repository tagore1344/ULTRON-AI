# backend/tests/test_evolution_9c1.py
import pytest
import datetime
import sqlite3
from unittest.mock import MagicMock

from core.evolution.evolution_policy import policy_9c1
from core.evolution.evolution_memory import evo_memory_9c1
from core.evolution.strategy_store import strategy_store_9c1
from core.evolution.evolution_manager import evolution_manager_9c1


@pytest.fixture(autouse=True)
def clean_evolution_tables():
    """Wipes all evolution tables before and after each test run to guarantee total isolation."""
    conn = evo_memory_9c1.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evolution_experiments")
    cursor.execute("DELETE FROM evolution_candidates")
    cursor.execute("DELETE FROM evolution_hypotheses")
    cursor.execute("DELETE FROM evolution_strategies")
    conn.commit()
    conn.close()

    # Reset manager status
    evolution_manager_9c1.enabled = False
    evolution_manager_9c1.state = "IDLE"

    yield

    conn = evo_memory_9c1.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evolution_experiments")
    cursor.execute("DELETE FROM evolution_candidates")
    cursor.execute("DELETE FROM evolution_hypotheses")
    cursor.execute("DELETE FROM evolution_strategies")
    conn.commit()
    conn.close()


def test_schema_initialization_completed():
    """Verify that all four required evolution tables exist in the context database on startup."""
    conn = evo_memory_9c1.get_connection()
    cursor = conn.cursor()

    # Assert tables can be queried
    cursor.execute("SELECT COUNT(*) FROM evolution_hypotheses")
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM evolution_candidates")
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM evolution_experiments")
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM evolution_strategies")
    assert cursor.fetchone()[0] == 0

    conn.close()


def test_hypothesis_persistence_and_retrieval():
    """Verify that a structured Hypothesis record can be persisted and fully retrieved."""
    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    h = {
        "id": "hyp_test_001",
        "trigger": "excessive transcription errors",
        "observed_problem": "tiny.en maps joke as je",
        "degradation_metrics": {"error_rate": 0.22, "latency_ms": 150.0},
        "root_cause": "tiny model lack parameters",
        "proposed_adaptation": {"speech_model": "base.en"},
        "predicted_outcomes": {"error_rate": 0.05},
        "evidence": ["log_line_312", "log_line_455"],
        "confidence": 0.88,
        "risk_class": "SAFE_AUTOMATIC",
        "status": "FORMULATED",
        "created_at": now_str
    }

    success = evo_memory_9c1.save_hypothesis(h)
    assert success is True

    # Retrieve and assert
    retrieved = evo_memory_9c1.get_hypothesis("hyp_test_001")
    assert retrieved is not None
    assert retrieved["id"] == "hyp_test_001"
    assert retrieved["observed_problem"] == "tiny.en maps joke as je"
    assert retrieved["degradation_metrics"]["error_rate"] == 0.22
    assert retrieved["proposed_adaptation"]["speech_model"] == "base.en"
    assert retrieved["evidence"] == ["log_line_312", "log_line_455"]


def test_candidate_persistence_and_retrieval():
    """Verify that structured, immutable candidates persist safely."""
    # We must save parent hypothesis first due to foreign key constraints if verified
    h_success = evo_memory_9c1.save_hypothesis({
        "id": "hyp_test_002", "trigger": "test", "observed_problem": "test",
        "degradation_metrics": {}, "root_cause": "test", "proposed_adaptation": {},
        "predicted_outcomes": {}, "evidence": [], "confidence": 0.5,
        "risk_class": "SAFE_AUTOMATIC", "status": "FORMULATED",
        "created_at": "2026-08-13T12:00:00Z"
    })
    assert h_success is True

    c = {
        "id": "cand_test_001",
        "hypothesis_id": "hyp_test_002",
        "baseline_configuration": {"speech_model": "tiny.en"},
        "candidate_configuration": {"speech_model": "base.en"},
        "expected_benefit": 0.15,
        "expected_cost": 2000,
        "risk_class": "SAFE_AUTOMATIC",
        "resource_budget": {"tokens": 5000, "runs": 10},
        "rollback_snapshot": {"speech_model": "tiny.en"},
        "status": "CREATED"
    }

    success = evo_memory_9c1.save_candidate(c)
    assert success is True

    # Retrieve and verify
    retrieved = evo_memory_9c1.get_candidate("cand_test_001")
    assert retrieved is not None
    assert retrieved["id"] == "cand_test_001"
    assert retrieved["baseline_configuration"]["speech_model"] == "tiny.en"
    assert retrieved["candidate_configuration"]["speech_model"] == "base.en"


def test_experiment_record_persistence_and_retrieval():
    """Verify background experiment ledger can log and retrieve trial runs."""
    h_success = evo_memory_9c1.save_hypothesis({
        "id": "hyp_test_003", "trigger": "t", "observed_problem": "t", "degradation_metrics": {},
        "root_cause": "t", "proposed_adaptation": {}, "predicted_outcomes": {}, "evidence": [],
        "confidence": 0.5, "risk_class": "SAFE_AUTOMATIC", "status": "FORMULATED",
        "created_at": "2026-08-13T12:00:00Z"
    })
    c_success = evo_memory_9c1.save_candidate({
        "id": "cand_test_002", "hypothesis_id": "hyp_test_003", "baseline_configuration": {},
        "candidate_configuration": {}, "expected_benefit": 0.1, "expected_cost": 500,
        "risk_class": "SAFE_AUTOMATIC", "resource_budget": {}, "rollback_snapshot": {}, "status": "CREATED"
    })
    assert h_success and c_success

    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    exp = {
        "id": "exp_test_001",
        "hypothesis_id": "hyp_test_003",
        "candidate_id": "cand_test_002",
        "baseline_identifier": "tiny.en",
        "candidate_identifier": "base.en",
        "sample_size_target": 50,
        "samples_run": 12,
        "token_budget": 5000,
        "tokens_spent": 1200,
        "created_at": now_str,
        "status": "ACTIVE"
    }

    success = evo_memory_9c1.save_experiment_record(exp)
    assert success is True

    retrieved = evo_memory_9c1.get_experiment_record("exp_test_001")
    assert retrieved is not None
    assert retrieved["id"] == "exp_test_001"
    assert retrieved["samples_run"] == 12
    assert retrieved["token_budget"] == 5000


def test_strategy_storage_and_blacklist_lookup():
    """Verify StrategyStore can log successfully promoted strategies and query blacklists to avoid infinite re-discovery."""
    task_pattern = "open chrome command"

    # 1. Assert initial state is clean
    assert strategy_store_9c1.is_blacklisted(task_pattern) is False
    assert strategy_store_9c1.get_strategy_config(task_pattern) is None

    # 2. Blacklist and assert
    strategy_store_9c1.blacklist_strategy(task_pattern)
    assert strategy_store_9c1.is_blacklisted(task_pattern) is True

    # 3. Save a promoted strategy and query
    promoted_pattern = "volume check pattern"
    strategy_store_9c1.save_strategy(promoted_pattern, {"volume_offset": 5}, success=True)
    assert strategy_store_9c1.is_blacklisted(promoted_pattern) is False

    config = strategy_store_9c1.get_strategy_config(promoted_pattern)
    assert config is not None
    assert config["volume_offset"] == 5


def test_duplicate_candidate_and_hypothesis_prevention():
    """Verify saving duplicate identifiers throws SQLite primary key violations cleanly."""
    h = {
        "id": "hyp_test_dup", "trigger": "t", "observed_problem": "t", "degradation_metrics": {},
        "root_cause": "t", "proposed_adaptation": {}, "predicted_outcomes": {}, "evidence": [],
        "confidence": 0.5, "risk_class": "SAFE_AUTOMATIC", "status": "FORMULATED",
        "created_at": "2026-08-13T12:00:00Z"
    }
    success1 = evo_memory_9c1.save_hypothesis(h)
    success2 = evo_memory_9c1.save_hypothesis(h) # Duplicate PK

    assert success1 is True
    assert success2 is False # Caught exception internally and failed gracefully


def test_policy_budget_validation():
    """Verify that the evolution policy engine enforces hard token caps correctly."""
    # Policy caps: daily_token_budget = 50000, experiment_token_budget = 5000
    assert policy_9c1.validate_budget(current_daily_spend=10000, experiment_cost_est=2000) is True

    # Exceed experiment token cap (max 5000)
    assert policy_9c1.validate_budget(current_daily_spend=10000, experiment_cost_est=6000) is False

    # Exceed daily token cap (max 50000)
    assert policy_9c1.validate_budget(current_daily_spend=48000, experiment_cost_est=3000) is False


def test_evolution_disabled_by_default_and_security_boundaries():
    """Verify that self-evolution is locked to DISABLED state on boot and sweep is blocked."""
    # Default state is idle & disabled
    assert evolution_manager_9c1.enabled is False
    assert evolution_manager_9c1.state == "IDLE"

    # Running sweep on disabled returns BLOCKED
    res = evolution_manager_9c1.trigger_observation_sweep()
    assert res == "BLOCKED"
    assert evolution_manager_9c1.state == "BLOCKED"

    # Verify enabling operates statefully
    evolution_manager_9c1.set_evolution_enabled(True)
    assert evolution_manager_9c1.enabled is True
