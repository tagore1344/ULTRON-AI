# core/context/self_model.py
import os
import logging
from typing import Dict, Any, List

try:
    import psutil
except Exception:
    psutil = None

logger = logging.getLogger("ultron-api")


class SelfModel:
    """Maintains a stateful structured representation of ULTRON's internal state, capabilities, and resources."""

    def __init__(self):
        self.autonomy_level = 3  # LEVEL 3 default (low-risk autonomous)
        self.confidence_calibration = 0.95
        self.health_status = "HEALTHY"

        # Explicit capabilities categorizations (KNOWN, UNKNOWN, UNVERIFIED, FAILED)
        self.capabilities: Dict[str, str] = {
            "local_speech_tts": "KNOWN",
            "pyaudio_input": "UNVERIFIED",       # Needs physical verification
            "windows_pycaw_volume": "UNVERIFIED", # Needs Windows endpoints
            "screen_screenshot": "KNOWN",
            "flutter_sdk_compiler": "UNKNOWN",
            "update_signature_signer": "FAILED"   # Banned on Evolution Engine (Key isolated)
        }

        # Model registers
        self.models_available: Dict[str, bool] = {
            "gemini": True,
            "openai": False,
            "deepseek": False
        }

        self.failure_locks: List[str] = []
        self.active_goals_count = 0

    def get_resource_state(self) -> Dict[str, Any]:
        """Queries CPU, RAM, and GPU telemetry in real-time."""
        cpu_pct = 0.0
        ram_used_mb = 0.0
        ram_total_mb = 16000.0

        if psutil is not None:
            try:
                cpu_pct = psutil.cpu_percent()
                mem = psutil.virtual_memory()
                ram_used_mb = float(mem.used) / (1024 * 1024)
                ram_total_mb = float(mem.total) / (1024 * 1024)
            except Exception as e:
                logger.error("Error reading psutil telemetry: %s", e)

        return {
            "cpu_percent": cpu_pct,
            "ram_used_mb": round(ram_used_mb, 2),
            "ram_total_mb": round(ram_total_mb, 2),
            "gpu_vram_used_mb": 0.0, # Default non-hardware bound fallback
            "gpu_vram_total_mb": 4096.0
        }

    def register_failure(self, node_intent: str):
        """Transition component state dynamically on frequent failures."""
        if node_intent not in self.failure_locks:
            self.failure_locks.append(node_intent)
            self.confidence_calibration = max(0.1, self.confidence_calibration - 0.15)
            logger.warning("Failure logged in self model for intent '%s'. Confidence degraded to %.2f", node_intent, self.confidence_calibration)

    def set_autonomy(self, level: int):
        """Allows policy changes to update the Self Model's tracked autonomy level."""
        self.autonomy_level = level

    def get_summary(self) -> Dict[str, Any]:
        """Compiles a complete, sanitized self-model snapshot."""
        # Sanitize keys from environmental checks to prevent leaks
        from core.agent.policy_engine import policy_engine

        # Verify dynamic environment variable presence to populate model availability
        self.models_available["openai"] = "OPENAI_API_KEY" in os.environ
        self.models_available["gemini"] = "GEMINI_API_KEY" in os.environ or "GOOGLE_API_KEY" in os.environ
        self.models_available["deepseek"] = "DEEPSEEK_API_KEY" in os.environ

        # Integration Hook: Sync active status to Neural Graph Entity
        try:
            from core.neural.event_memory import event_memory
            event_memory.record_state("self_model_status", f"Self Model Health: {self.health_status}", belief_confidence=self.confidence_calibration)
        except Exception:
            pass

        return {
            "autonomy_level": self.autonomy_level,
            "health_status": self.health_status,
            "confidence_calibration": round(self.confidence_calibration, 2),
            "capabilities": self.capabilities,
            "models_available": self.models_available,
            "failure_locks": self.failure_locks,
            "resources": self.get_resource_state(),
            "tool_calls_spent_today": policy_engine.tool_calls_count
        }


# Singleton self-model tracker
self_model = SelfModel()
