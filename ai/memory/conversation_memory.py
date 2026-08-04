# ai/memory/conversation_memory.py — Persistent conversation memory
import json
import os
import datetime


class ConversationMemory:
    """Stores conversation history in a JSON file."""

    def __init__(self, memory_file="ultron_memory.json"):
        self.memory_file = memory_file
        self.memory = self.load_memory()

    def load_memory(self):
        if not os.path.exists(self.memory_file):
            return {
                "user_name": "",
                "preferences": {},
                "conversations": [],
                "notes": [],
            }

        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "user_name": "",
                "preferences": {},
                "conversations": [],
                "notes": [],
            }

    def save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=4)
        except Exception:
            pass

    def add_conversation(self, user, assistant, limit=50):
        self.memory["conversations"].append(
            {
                "time": str(datetime.datetime.now()),
                "user": user,
                "assistant": assistant,
            }
        )
        self.memory["conversations"] = self.memory["conversations"][-limit:]
        self.save_memory()

    def get_conversations(self, limit=None):
        conversations = self.memory.get("conversations", [])
        if limit:
            return conversations[-limit:]
        return conversations

    def clear_conversations(self):
        self.memory["conversations"] = []
        self.save_memory()

    def set_user_name(self, name):
        self.memory["user_name"] = name
        self.save_memory()

    def get_user_name(self):
        return self.memory.get("user_name", "")

    def add_note(self, note):
        self.memory["notes"].append(note)
        self.save_memory()

    def get_notes(self):
        return self.memory.get("notes", [])