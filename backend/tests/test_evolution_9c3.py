# backend/tests/test_evolution_9c3.py
import pytest
import datetime
import sqlite3
from unittest.mock import MagicMock, patch

from core.evolution.experiment_manager import experiment_manager_9c3
from core.evolution.evaluator import evaluator_9c3
from core.evolution.evolution_policy import policy_9c1
from core.evolution.evolution_memory import evo_memory_9c1


@pytest.fixture(autouse=True)
def clean_experiment_and_evaluator_states():
    """Wipes all evolution databases and resets state coordinates before and after each test."""
    conn = evo_memory_9c1.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evolution_experiments")
    cursor.execute("DELETE FROM evolution_candidates")
    cursor.execute("DELETE FROM evolution_hypotheses")
    cursor.execute("DELETE FROM evolution_strategies")
    conn.commit()
    conn.close()

    experiment_manager_9c3.active_experiment = None
    experiment_manager_9c3.enabled = False

    # Reset evaluator thresholds to standard default limits
    evaluator_9c3.min_sample_count = 30
    evaluator_9c3.min_improvement_pct = 0.05
    evaluator_9c3.max_latency_regression_pct = 0.10
    evaluator_9c3.max_error_regression_pct = 0.02

    yield

    conn = evo_memory_9c1.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evolution_experiments")
    cursor.execute("DELETE FROM evolution_candidates")
    cursor.execute("DELETE FROM evolution_hypotheses")
    cursor.execute("DELETE FROM evolution_strategies")
    conn.commit()
    conn.close()


def test_evolution_disabled_behavior_default():
    """Verify that by default, when disabled, all routing resolves cleanly to BASELINE."""
    experiment_manager_9c3.enabled = False
    experiment_manager_9c3.create_experiment(
        experiment_id="exp_001",
        hypothesis_id="hyp_001",
        candidate_id="cand_001",
        baseline_id="base_001"
    )

    # Even with an active experiment, if disabled, resolves to BASELINE
    cohort = experiment_manager_9c3.determine_cohort("session_abc")
    assert cohort == "BASELINE"


def test_cohort_routing_ratio_and_deterministic_assignment():
    """Verify that cohort selection correctly splits traffic and maps session IDs deterministically."""
    experiment_manager_9c3.set_experiment_enabled(True)

    # 1. Test 5% default cohort routing
    experiment_manager_9c3.create_experiment(
        experiment_id="exp_ratio_5",
        hypothesis_id="hyp_001",
        candidate_id="cand_001",
        baseline_id="base_001",
        cohort_ratio=0.05
    )

    # Session ID determinism test
    cohort_1 = experiment_manager_9c3.determine_cohort("session_user_999")
    cohort_2 = experiment_manager_9c3.determine_cohort("session_user_999")
    assert cohort_1 == cohort_2 # Must remain absolute deterministic for the same session ID

    # Test scaling back ratios over maximum cap (50%)
    experiment_manager_9c3.create_experiment(
        experiment_id="exp_max_cap",
        hypothesis_id="hyp_001",
        candidate_id="cand_001",
        baseline_id="base_001",
        cohort_ratio=0.85 # Proposed 85% rollout
    )
    assert experiment_manager_9c3.active_experiment["cohort_ratio"] == 0.50 # Enforced scaleback cap


def test_dry_run_side_effect_blocking():
    """Verify that candidate cohorts run system-affecting tools in Dry-Run Mock mode exclusively."""
    # Candidate cohort blocks physical launches and adjustments
    assert experiment_manager_9c3.get_dry_run_safety_flag("app.open", "CANDIDATE") is True
    assert experiment_manager_9c3.get_dry_run_safety_flag("shutdown", "CANDIDATE") is True
    assert experiment_manager_9c3.get_dry_run_safety_flag("system.volume_up", "CANDIDATE") is True
    assert experiment_manager_9c3.get_dry_run_safety_flag("app.send_message", "CANDIDATE") is True

    # Baseline cohort never gets blocked (runs real tools)
    assert experiment_manager_9c3.get_dry_run_safety_flag("app.open", "BASELINE") is False

    # Safe non-side-effecting tools are allowed normally
    assert experiment_manager_9c3.get_dry_run_safety_flag("system.info", "CANDIDATE") is False
    assert experiment_manager_9c3.get_dry_run_safety_flag("system.time", "CANDIDATE") is False


def test_token_budget_enforcement_and_baseline_restoration():
    """Verify exceeding the experiment budget cancels active trials and restores baseline configuration."""
    experiment_manager_9c3.set_experiment_enabled(True)
    experiment_manager_9c3.create_experiment(
        experiment_id="exp_budget_test",
        hypothesis_id="hyp_001",
        candidate_id="cand_001",
        baseline_id="base_001",
        token_budget=1000
    )

    # Artificially force budget exhaustion
    experiment_manager_9c3.active_experiment["tokens_spent"] = 1100

    # The next trial routing must exceed budget, triggering automatic timeout cancellation
    cohort = experiment_manager_9c3.determine_cohort("session_trial_exceeded")
    assert cohort == "BASELINE"
    assert experiment_manager_9c3.active_experiment["status"] == "CANCELLED"
    assert "Budget exhausted" in experiment_manager_9c3.active_experiment["cancellation_reason"]

    # Verify further routing fails closed to BASELINE
    assert experiment_manager_9c3.determine_cohort("session_new") == "BASELINE"


def test_timeout_enforcement_after_24h():
    """Verify that trials older than 24 hours are automatically cancelled and rolled back."""
    experiment_manager_9c3.set_experiment_enabled(True)
    experiment_manager_9c3.create_experiment(
        experiment_id="exp_timeout_test",
        hypothesis_id="hyp_001",
        candidate_id="cand_001",
        baseline_id="base_001"
    )

    # Artificially shift start time back 25 hours
    dt = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=25)
    experiment_manager_9c3.active_experiment["start_time"] = dt.isoformat() + "Z"

    # Next cohort routing check should catch timeout and cancel
    cohort = experiment_manager_9c3.determine_cohort("session_user")
    assert cohort == "BASELINE"
    assert experiment_manager_9c3.active_experiment["status"] == "CANCELLED"
    assert "timeout" in experiment_manager_9c3.active_experiment["cancellation_reason"].lower()


def test_sample_size_enforcement_and_insufficient_rejection():
    """Verify that evaluation is blocked and returns INSUFFICIENT_SAMPLES when targets are unfulfilled."""
    verdict, explanation = evaluator_9c3.evaluate_cohorts(
        samples_run=15, # Required is 30
        baseline_metrics={"success_rate": 0.90},
        candidate_metrics={"success_rate": 0.95}
    )

    assert verdict == "INSUFFICIENT_SAMPLES"
    assert "Insufficient sample size" in explanation


def test_evaluator_rejection_recommendations():
    """Verify that the evaluator recommends REJECT_RECOMMENDED when regressions occur or benefits are unreached."""
    # 1. Reject on low success rate improvement (minimum benefit target is 5% delta)
    verdict, explanation = evaluator_9c3.evaluate_cohorts(
        samples_run=35,
        baseline_metrics={"success_rate": 0.90, "latency_sec": 0.1, "error_rate": 0.0},
        candidate_metrics={"success_rate": 0.93, "latency_sec": 0.1, "error_rate": 0.0} # Only +3%
    )
    assert verdict == "REJECT_RECOMMENDED"
    assert "below the required threshold" in explanation

    # 2. Reject on excessive latency regression (max 10% allowed)
    verdict, explanation = evaluator_9c3.evaluate_cohorts(
        samples_run=35,
        baseline_metrics={"success_rate": 0.90, "latency_sec": 0.10, "error_rate": 0.0},
        candidate_metrics={"success_rate": 0.96, "latency_sec": 0.15, "error_rate": 0.0} # +50% latency
    )
    assert verdict == "REJECT_RECOMMENDED"
    assert "excessive latency overhead" in explanation

    # 3. Reject on critical policy/security violations
    verdict, explanation = evaluator_9c3.evaluate_cohorts(
        samples_run=35,
        baseline_metrics={"success_rate": 0.90},
        candidate_metrics={"success_rate": 0.96},
        critical_policy_violations=1
    )
    assert verdict == "REJECT_RECOMMENDED"
    assert "breached 1 policy" in explanation


def test_evaluator_promotion_recommendation():
    """Verify that the evaluator outputs PROMOTE_RECOMMENDED when the candidate meets all benchmarks."""
    verdict, explanation = evaluator_9c3.evaluate_cohorts(
        samples_run=35,
        baseline_metrics={"success_rate": 0.90, "latency_sec": 0.20, "error_rate": 0.05},
        candidate_metrics={"success_rate": 0.96, "latency_sec": 0.21, "error_rate": 0.04} # +6% success, +5% latency, -1% error
    )
    assert verdict == "PROMOTE_RECOMMENDED"
    assert "outstanding improvement" in explanation
