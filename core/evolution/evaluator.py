# core/evolution/evaluator.py
import logging
from typing import Dict, Any, Tuple

from core.evolution.evolution_policy import policy_9c1

logger = logging.getLogger("ultron-api")


class Evaluator:
    """Computes statistical improvement deltas and outputs advisory PROMOTE_RECOMMENDED or REJECT_RECOMMENDED verdicts."""

    def __init__(self):
        # Allow custom override of thresholds for testing/flexibility
        self.min_sample_count = policy_9c1.min_sample_count
        self.min_improvement_pct = policy_9c1.min_improvement_pct
        self.max_latency_regression_pct = policy_9c1.max_latency_regression_pct
        self.max_error_regression_pct = policy_9c1.max_error_regression_pct

    def evaluate_cohorts(
        self,
        samples_run: int,
        baseline_metrics: Dict[str, float],
        candidate_metrics: Dict[str, float],
        critical_policy_violations: int = 0
    ) -> Tuple[str, str]:
        """
        Evaluates candidate performance against baseline metrics.
        Returns a tuple: (verdict_status, explanation_reason).
        Verdicts: PROMOTE_RECOMMENDED, REJECT_RECOMMENDED, or INSUFFICIENT_SAMPLES.
        """
        # 1. Sample Size Check
        if samples_run < self.min_sample_count:
            reason = f"Insufficient sample size ({samples_run}/{self.min_sample_count}). Testing must continue."
            logger.info("Evaluation result: INSUFFICIENT_SAMPLES. Reason: %s", reason)
            return "INSUFFICIENT_SAMPLES", reason

        # 2. Critical Security Check
        if critical_policy_violations > 0:
            reason = f"Candidate breached {critical_policy_violations} policy/security boundaries. Rejecting."
            logger.warning("Evaluation result: REJECT_RECOMMENDED. Reason: %s", reason)
            return "REJECT_RECOMMENDED", reason

        # Extract primary metrics
        b_success = baseline_metrics.get("success_rate", 0.0)
        c_success = candidate_metrics.get("success_rate", 0.0)

        b_latency = baseline_metrics.get("latency_sec", 1.0)
        c_latency = candidate_metrics.get("latency_sec", 1.0)

        b_error = baseline_metrics.get("error_rate", 0.0)
        c_error = candidate_metrics.get("error_rate", 0.0)

        # 3. Success Rate Evaluation
        success_improvement = c_success - b_success
        if success_improvement < self.min_improvement_pct:
            reason = f"Candidate success improvement ({success_improvement:.2%}) is below the required threshold ({self.min_improvement_pct:.1%})."
            logger.info("Evaluation result: REJECT_RECOMMENDED. Reason: %s", reason)
            return "REJECT_RECOMMENDED", reason

        # 4. Latency Regression Check
        latency_overhead = (c_latency - b_latency) / max(0.01, b_latency)
        if latency_overhead > self.max_latency_regression_pct:
            reason = f"Candidate introduced excessive latency overhead ({latency_overhead:.2%}), breaching the cap ({self.max_latency_regression_pct:.1%})."
            logger.warning("Evaluation result: REJECT_RECOMMENDED. Reason: %s", reason)
            return "REJECT_RECOMMENDED", reason

        # 5. Error Rate Regression Check
        error_regression = c_error - b_error
        if error_regression > self.max_error_regression_pct:
            reason = f"Candidate introduced excessive error rate regression ({error_regression:.2%}), breaching the cap ({self.max_error_regression_pct:.1%})."
            logger.warning("Evaluation result: REJECT_RECOMMENDED. Reason: %s", reason)
            return "REJECT_RECOMMENDED", reason

        # Success! Output recommendation to promote
        reason = f"Candidate demonstrated outstanding improvement (+{success_improvement:.2%}) and complies with all regression thresholds."
        logger.info("Evaluation result: PROMOTE_RECOMMENDED. Reason: %s", reason)
        return "PROMOTE_RECOMMENDED", reason


evaluator_9c3 = Evaluator()
