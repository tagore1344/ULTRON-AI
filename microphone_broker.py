# microphone_broker.py
import threading
from enum import Enum


class MicState(str, Enum):
    IDLE = "IDLE"
    WAKE_LISTENING = "WAKE_LISTENING"
    SUSPENDING = "SUSPENDING"
    VERIFYING = "VERIFYING"
    COMMAND_LISTENING = "COMMAND_LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    RESUMING = "RESUMING"


class MicrophoneResourceBroker:
    """Statefully manages exclusive microphone hardware access, preventing concurrent PyAudio contention."""

    def __init__(self):
        self._state = MicState.IDLE
        self._active_owner = None
        self._lock = threading.Lock()

    @property
    def state(self) -> MicState:
        return self._state

    @property
    def active_owner(self) -> str:
        return self._active_owner

    def acquire(self, owner_name: str, target_state: MicState) -> bool:
        """Exclusively lock and allocate microphone resource to a specific caller context."""
        with self._lock:
            if self._active_owner is not None and self._active_owner != owner_name:
                print(f"[VOICE ERROR] Concurrency violation: '{owner_name}' failed to acquire mic. Held by '{self._active_owner}'")
                return False

            self._active_owner = owner_name
            self._state = target_state
            print(f"[VOICE] Microphone acquired: {owner_name} (State: {target_state.value})")
            return True

    def release(self, owner_name: str):
        """Release microphone resource locks cleanly, returning system state to IDLE."""
        with self._lock:
            if self._active_owner == owner_name:
                print(f"[VOICE] Microphone released: {owner_name}")
                self._active_owner = None
                self._state = MicState.IDLE


# Global broker singleton instance
mic_broker = MicrophoneResourceBroker()
