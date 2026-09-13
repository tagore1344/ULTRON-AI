# backend/services/ultron_service.py
import logging
from core.brain.ai_brain import AIBrain

logger = logging.getLogger("ultron-api")


class UltronService:
    """Service adapter bridging the FastAPI backend to the existing ULTRON-AI Core."""

    def __init__(self):
        try:
            self.brain = AIBrain()
            logger.info("UltronService adapter connected to canonical AIBrain successfully.")
        except Exception as e:
            logger.critical("Failed to connect to AIBrain: %s", e, exc_info=True)
            self.brain = None

    def ask_brain(self, message: str) -> str:
        """Send user input to the AIBrain and obtain normalized responses."""
        if self.brain is None:
            logger.error("AIBrain instance is unavailable.")
            raise RuntimeError("ULTRON Brain system is offline.")

        try:
            logger.info("Dispatching query to ULTRON Brain Core...")
            response = self.brain.think(message)
            logger.info("Successfully received response from ULTRON Brain Core.")
            return response
        except Exception as e:
            logger.error("Error communicating with ULTRON Brain: %s", e, exc_info=True)
            raise RuntimeError(f"Brain execution failure: {e}")


# Singleton instance of the service adapter
ultron_service = UltronService()
