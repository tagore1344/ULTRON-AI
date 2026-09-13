# backend/tests/test_evolution_9c2.py
import pytest
import sqlite3
import datetime
import json
from unittest.mock import MagicMock, patch

from core.context.memory_manager import memory_manager
from core.evolution.evolution_memory import evo_memory_9c1
from core.evolution.hypothesis_engine import hypothesis_engine
from core.evolution.candidate_manager import candidate_manager
from core.evolution.evolution_manager import evolution_manager_9c1


@pytest.fixture(autouse=True)
def clean_context_and_evolution_tables():
    """Ensure that the context memory and evolution tables are completely clean and isolated."""
    memory_manager.clear_all_context_memory()

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

    memory_manager.clear_all_context_memory()
    conn = evo_memory_9c1.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evolution_experiments")
    cursor.execute("DELETE FROM evolution_candidates")
    cursor.execute("DELETE FROM evolution_hypotheses")
    cursor.execute("DELETE FROM evolution_strategies")
    conn.commit()
    conn.close()


def test_recurring_failure_detection_and_hypothesis_generation():
    """Verify that HypothesisEngine scans failure history, detects recurring failures, and compiles hypotheses."""
    # 1. Seed FailureMemory with 3 repeated failures of 'open chroome'
    for _ in range(3):
        memory_manager.add_failure_memory(
            task_pattern="open chroome",
            failed_node_intent="app.open",
            error_signature="application not found",
            recovery_decision_applied="FAIL",
            context_snapshot="{}"
        )

    # 2. Trigger Scan
    weaknesses = hypothesis_engine.scan_for_weaknesses()
    assert len(weaknesses) >= 1
    assert weaknesses[0]["type"] == "REPEATED_FAILURE"
    assert weaknesses[0]["pattern"] == "open chroome"
    assert weaknesses[0]["frequency"] == 3

    # 3. Generate Hypothesis
    hypothesis = hypothesis_engine.propose_hypothesis(weaknesses[0])
    assert hypothesis is not None
    assert hypothesis["observed_problem"] == "Voice transcription mapped Chrome launch as 'open chroome' which failed intent routing"
    assert hypothesis["proposed_adaptation"] == {"command_alias": {"chroome": "chrome"}}
    assert hypothesis["confidence"] == 0.98
    assert hypothesis["risk_class"] == "SAFE_AUTOMATIC"


def test_duplicate_hypothesis_prevention():
    """Verify that HypothesisEngine detects prior hypotheses and blocks duplicate generation."""
    weakness = {
        "type": "REPEATED_FAILURE",
        "pattern": "open chroome",
        "frequency": 3,
        "errors": []
    }

    # Generate and save first hypothesis
    h = hypothesis_engine.propose_hypothesis(weakness)
    assert h is not None
    assert evo_memory_9c1.save_hypothesis(h) is True

    # Try proposing a second one for the same pattern
    h_dup = hypothesis_engine.propose_hypothesis(weakness)
    assert h_dup is None # Duplicate check blocks creation


def test_candidate_creation_and_risk_classification():
    """Verify CandidateManager can create candidates with correct risk ratings and rollback snapshots."""
    h = {
        "id": "hyp_9c2_test",
        "observed_problem": "tiny.en maps joke as je",
        "proposed_adaptation": {"command_alias": {"chroome": "chrome"}},
        "predicted_outcomes": {"error_rate": 0.05},
        "risk_class": "SAFE_AUTOMATIC",
        "created_at": "2026-08-13T12:00:00Z"
    }

    c = candidate_manager.create_candidate(h)
    assert c is not None
    assert c["id"].startswith("cand_")
    assert c["hypothesis_id"] == "hyp_9c2_test"
    assert c["candidate_configuration"] == {"command_alias": {"chroome": "chrome"}}
    assert c["risk_class"] == "SAFE_AUTOMATIC"
    assert c["status"] == "CREATED"
    assert c["rollback_snapshot"] == {"command_alias": {}}


def test_malicious_and_source_code_candidate_rejections():
    """Verify CandidateManager strictly rejects un-allowlisted configurations, subprocess, shell, or code payloads."""
    # 1. Malicious python payload
    malicious_h = {
        "id": "hyp_malicious",
        "observed_problem": "exploit",
        "proposed_adaptation": {"command_alias": {"exploit": "import os; os.system('rm -rf /')"}},
        "risk_class": "SAFE_AUTOMATIC"
    }
    c_malicious = candidate_manager.create_candidate(malicious_h)
    assert c_malicious is None # Blocked by validation

    # 2. Blocked un-allowlisted configuration keys
    invalid_key_h = {
        "id": "hyp_invalid_key",
        "observed_problem": "invalid",
        "proposed_adaptation": {"banned_security_key": {"port": 80}},
        "risk_class": "SAFE_AUTOMATIC"
    }
    c_invalid = candidate_manager.create_candidate(invalid_key_h)
    assert c_invalid is None # Blocked


def test_source_change_requests_proposal_only_protection():
    """Verify that a source-code level hypothesis is compiled as a CHANGE_PROPOSAL only, and is blocked from execution."""
    source_h = {
        "id": "hyp_source_id",
        "trigger": "fails on wake",
        "observed_problem": "voice ID failures on ambient noise",
        "degradation_metrics": {"error_rate": 0.35},
        "root_cause": "voice_id.py lacks dynamic thresholding",
        "proposed_adaptation": {"change_proposal": {"file": "voice_id.py", "diff": "@@ -20,2 @@"}},
        "predicted_outcomes": {"error_rate": 0.02},
        "risk_class": "HIGH_RISK"
    }

    c = candidate_manager.create_candidate(source_h)
    assert c is not None
    assert c["risk_class"] == "HIGH_RISK"
    assert c["status"] == "REJECTED" # Permanently locked out from automatic execution
    assert c["resource_budget"] == {"tokens": 0, "runs": 0} # Prevented from using budget resources


def test_disabled_evolution_behavior_preservation():
    """Verify that the evolution manager remains disabled on boot and blocks observation sweeps."""
    assert evolution_manager_9c1.enabled is False
    res = evolution_manager_9c1.trigger_observation_sweep()
    assert res == "BLOCKED"
