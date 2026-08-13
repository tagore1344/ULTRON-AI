# core/evolution/evolution_policy.py
import datetime


class EvolutionPolicy:
    """Enforces absolute resource limits, progressive cohort rollout ratios, and configurable promotion criteria."""

    def __init__(self):
        # 1. Hard Limits (Resource Governance)
        self.daily_token_budget = 50000
        self.experiment_token_budget = 5000
        self.max_concurrent_experiments = 1
        self.max_candidates_per_hypothesis = 5
        self.max_evolution_depth = 3
        self.experiment_timeout_seconds = 86400  # 24 hours
        self.resource_overhead_limit = 0.10  # 10% maximum RAM/CPU overhead

        # 2. Progressive Cohort Rollout Policy
        self.initial_rollout_ratio = 0.05  # Start with 5% candidate / 95% baseline
        self.progressive_rollout_steps = [0.05, 0.15, 0.30, 0.50]

        # 3. Configurable Promotion Policies
        self.min_sample_count = 30
        self.min_improvement_pct = 0.05  # 5% minimum improvement required
        self.max_latency_regression_pct = 0.10  # Max 10% latency regression acceptable
        self.max_error_regression_pct = 0.02  # Max 2% error rate regression acceptable
        self.stability_window_hours = 48  # Verification window hours

    def validate_budget(self, current_daily_spend: int, experiment_cost_est: int) -> bool:
        """Checks if initiating a new experiment complies with resource token caps."""
        if current_daily_spend + experiment_cost_est > self.daily_token_budget:
            return False
        if experiment_cost_est > self.experiment_token_budget:
            return False
        return True


policy_9c1 = EvolutionPolicy()
