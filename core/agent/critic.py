# core/agent/critic.py
import logging

logger = logging.getLogger("ultron-api")


class Critic:
    """Evaluates task execution results, detects anomalies, and flags nodes as successful or failed."""

    def evaluate_result(self, result: str) -> bool:
        """Audits the returned string; returns True if successful, False if failure is detected."""
        res_lower = str(result).lower().strip()

        # Detect clear failure signatures
        failure_signals = ["failed", "unavailable", "error", "not found", "offline", "trapped"]
        for signal in failure_signals:
            if signal in res_lower:
                logger.warning("Critic detected execution anomaly/failure: '%s'", result)
                return False

        logger.info("Critic verified execution success.")
        return True


critic = Critic()
