# ai/memory/session_memory.py — In-memory session state
import time


class SessionMemory:
    """Stores ephemeral session state (not persisted to disk)."""

    def __init__(self):
        self.data = {}
        self.created_at = time.time()

    def set(self, key, value):
        """Store a value in the session."""
        self.data[key] = value

    def get(self, key, default=None):
        """Retrieve a value from the session."""
        return self.data.get(key, default)

    def has(self, key):
        """Check if a key exists in the session."""
        return key in self.data

    def delete(self, key):
        """Remove a key from the session."""
        if key in self.data:
            del self.data[key]

    def clear(self):
        """Clear all session data."""
        self.data.clear()

    def set_user_name(self, name):
        self.set("user_name", name)

    def get_user_name(self):
        return self.get("user_name", "")

    def set_last_intent(self, intent):
        self.set("last_intent", intent)

    def get_last_intent(self):
        return self.get("last_intent", "chat")

    def set_context(self, context):
        self.set("context", context)

    def get_context(self):
        return self.get("context", {})

    def age_seconds(self):
        """Return how many seconds the session has been alive."""
        return time.time() - self.created_at