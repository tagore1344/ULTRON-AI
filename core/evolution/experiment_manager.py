# core/evolution/experiment_manager.py
import datetime
import logging
import hashlib
from typing import Dict, Any, Optional

from core.evolution.evolution_memory import evo_memory_9c1
from core.evolution.evolution_policy import policy_9c1
from core.context.memory_manager import memory_manager

logger = logging.getLogger("ultron-api")


class ExperimentManager:
    """Manages secure, bounded A/B cohort routing, enforces trial budgets, and coordinates dry-run safety locks."""

    def __init__(self):
        self.active_experiment: Optional[Dict[str, Any]] = None
        self.enabled = False # Locked to disabled by default

    def set_experiment_enabled(self, enabled: bool):
        """Sets the policy enable status for active experiments."""
        self.enabled = enabled
        logger.info("Experiment system state set to: %s", "ENABLED" if enabled else "DISABLED")

    def create_experiment(
        self,
        experiment_id: str,
        hypothesis_id: str,
        candidate_id: str,
        baseline_id: str,
        cohort_ratio: float = 0.05, # Default 5% candidate / 95% baseline
        sample_size_target: int = 30,
        token_budget: int = 5000
    ) -> Dict[str, Any]:
        """Formulates and registers a new experiment model."""
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

        # Hard constraint check
        if cohort_ratio > 0.50:
            logger.warning("Policy block: Rollout ratio %f exceeds maximum allowed (50%%). Scaling back to 50%%.", cohort_ratio)
            cohort_ratio = 0.50

        exp = {
            "id": experiment_id,
            "hypothesis_id": hypothesis_id,
            "candidate_id": candidate_id,
            "baseline_id": baseline_id,
            "cohort_ratio": cohort_ratio,
            "sample_size_target": sample_size_target,
            "samples_run": 0,
            "token_budget": token_budget,
            "tokens_spent": 0,
            "start_time": now_str,
            "end_time": None,
            "status": "CREATED",
            "cancellation_reason": None,
            "environment_snapshot": "Headless Linux Container"
        }

        self.active_experiment = exp

        # Persist in Database
        evo_memory_9c1.save_experiment_record({
            "id": experiment_id,
            "hypothesis_id": hypothesis_id,
            "candidate_id": candidate_id,
            "baseline_identifier": baseline_id,
            "candidate_identifier": candidate_id,
            "sample_size_target": sample_size_target,
            "samples_run": 0,
            "token_budget": token_budget,
            "tokens_spent": 0,
            "created_at": now_str,
            "status": "ACTIVE"
        })

        logger.info("Successfully registered and persisted Experiment: %s (Ratio: %.2f)", experiment_id, cohort_ratio)
        return exp

    def determine_cohort(self, session_id: str) -> str:
        """
        Determines if an incoming request is routed to BASELINE or CANDIDATE.
        Enforces a deterministic split based on session ID hashing.
        """
        if not self.enabled or not self.active_experiment:
            return "BASELINE"

        # Check status bounds
        status = self.active_experiment.get("status", "CREATED")
        if status in ("CANCELLED", "FAILED", "COMPLETED"):
            return "BASELINE"

        # Check Budget Exhaustion
        if self.active_experiment["tokens_spent"] >= self.active_experiment["token_budget"]:
            self.cancel_experiment("Budget exhausted")
            return "BASELINE"

        # Check Timeout (24h)
        start_dt = datetime.datetime.fromisoformat(self.active_experiment["start_time"].replace("Z", ""))
        age_hours = (datetime.datetime.now() - start_dt).total_seconds() / 3600.0
        if age_hours > 24.0:
            self.cancel_experiment("Experiment timeout exceeded (24h)")
            return "BASELINE"

        # Deterministic hash split
        hash_val = int(hashlib.md5(session_id.encode('utf-8')).hexdigest(), 16)
        bucket = hash_val % 100

        ratio_cutoff = self.active_experiment.get("cohort_ratio", 0.05) * 100
        if bucket < ratio_cutoff:
            # Route to Candidate Cohort
            self.active_experiment["samples_run"] += 1
            # Spend simulated token budget
            self.active_experiment["tokens_spent"] += 100
            return "CANDIDATE"
        else:
            return "BASELINE"

    def cancel_experiment(self, reason: str):
        """Cancels the active experiment statefully, logging the reason and restoring baseline."""
        if self.active_experiment:
            self.active_experiment["status"] = "CANCELLED"
            self.active_experiment["cancellation_reason"] = reason
            self.active_experiment["end_time"] = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

            logger.warning("Experiment %s CANCELLED. Reason: '%s'. Restoring baseline.", self.active_experiment["id"], reason)

            # Update DB
            conn = evo_memory_9c1.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE evolution_experiments SET status = 'CANCELLED' WHERE experiment_id = ?",
                (self.active_experiment["id"],)
            )
            conn.commit()
            conn.close()

    def get_dry_run_safety_flag(self, intent: str, cohort: str) -> bool:
        """
        Returns True if a system-affecting tool must be executed in Dry-Run Mock mode.
        Forces all candidate trials to run system-affecting tools as Dry-Run for safety.
        """
        if cohort != "CANDIDATE":
            return False

        # System-affecting triggers
        system_affecting = [
            "shutdown", "restart", "system.volume_up", "system.volume_down",
            "app.open", "app.send_message"
        ]
        return intent in system_affecting


# Singleton instance
experiment_manager_9c3 = ExperimentManager()
