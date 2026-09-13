# core/evolution/evolution_manager.py
import logging
from typing import Dict, Any

logger = logging.getLogger("ultron-api")


class EvolutionManager:
    """The master coordinator managing loop states and enforcing baseline-only execution safety."""

    def __init__(self):
        # Evolution is strictly disabled by default (Safety Lock)
        self.enabled = False

        # State machine initialized to IDLE
        self.state = "IDLE"

    def set_evolution_enabled(self, enable: bool) -> bool:
        """Safely enable or disable active self-evolution state."""
        self.enabled = enable
        logger.info("Self-evolution state set to: %s", "ENABLED" if enable else "DISABLED")
        return self.enabled

    def get_status(self) -> Dict[str, Any]:
        """Returns the current operational state of the evolution manager."""
        return {
            "evolution_enabled": self.enabled,
            "state": self.state
        }

    def trigger_observation_sweep(self) -> str:
        """
        Attempts to scan for weaknesses and initiate experiments.
        Strictly fails-closed and blocks execution if self-evolution is disabled.
        """
        if not self.enabled:
            self.state = "BLOCKED"
            logger.warning("Observation sweep aborted: Self-evolution is currently disabled by policy.")
            return "BLOCKED"

        self.state = "OBSERVING"
        logger.info("Initiating weakness scan sweep...")

        # Under Phase 9C-1, automatic experiment execution is not yet implemented.
        # We transition cleanly back to IDLE to comply with phase boundaries.
        self.state = "IDLE"
        return "IDLE"


# Singleton coordinator
evolution_manager_9c1 = EvolutionManager()
