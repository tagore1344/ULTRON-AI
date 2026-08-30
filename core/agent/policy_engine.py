# core/agent/policy_engine.py
import logging
from enum import IntEnum

logger = logging.getLogger("ultron-api")


class AutonomyLevel(IntEnum):
    LEVEL_0 = 0  # Answer only (Passive)
    LEVEL_1 = 1  # Suggest actions
    LEVEL_2 = 2  # Execute approved actions (manual confirmation required for all)
    LEVEL_3 = 3  # Autonomous low-risk (auto-run SAFE, confirm CONFIRMATION_REQUIRED)
    LEVEL_4 = 4  # Long-horizon autonomous
    LEVEL_5 = 5  # Self-evolution / research


class PolicyEngine:
    """Enforces resource budgets, maximum tool call counts, and autonomy-level constraints securely."""

    def __init__(self):
        self.autonomy_level = AutonomyLevel.LEVEL_3  # Default safe level

        # Hard limits
        self.max_tool_calls = 10
        self.max_recursion_depth = 5
        self.token_budget = 10000

        # Spent counters
        self.tool_calls_count = 0
        self.tokens_spent = 0

    def set_autonomy(self, level: int) -> bool:
        """Safely set the active autonomy level."""
        try:
            self.autonomy_level = AutonomyLevel(level)
            logger.info("Autonomy level set to: %s", self.autonomy_level.name)
            return True
        except ValueError:
            logger.error("Invalid autonomy level specified: %s", level)
            return False

    def validate_action(self, intent: str, risk_class: str) -> bool:
        """
        Policy check before execution.
        Asserts that resource budgets and autonomy permissions are fully satisfied.
        """
        # 1. Enforce hard tool-call limit
        if self.tool_calls_count >= self.max_tool_calls:
            logger.warning("Policy block: Max tool-call limit (%d) exceeded.", self.max_tool_calls)
            return False

        # 2. Enforce token budget limit
        if self.tokens_spent >= self.token_budget:
            logger.warning("Policy block: Token budget (%d) exceeded.", self.token_budget)
            return False

        # 3. Enforce Autonomy Level boundaries statefully
        if self.autonomy_level == AutonomyLevel.LEVEL_0:
            # Passive: Blocks all system execution
            logger.warning("Policy block: Autonomy level is LEVEL_0. Execution prohibited.")
            return False

        if risk_class == "HIGH_RISK":
            # HIGH_RISK always fails closed / blocked inside the agent loop
            logger.warning("Policy block: HIGH_RISK command executed over agent loop blocked.")
            return False

        return True

    def increment_tool_call(self):
        self.tool_calls_count += 1

    def spend_tokens(self, amount: int):
        self.tokens_spent += amount

    def reset_counters(self):
        self.tool_calls_count = 0
        self.tokens_spent = 0


policy_engine = PolicyEngine()
