# memory_engine.py
import json
import os
import datetime


class MemoryEngine:

    def __init__(self):
        # ULTRON memory with one-time migration from the legacy jarvis_memory.json
        self.memory_file = "ultron_memory.json"
        self.memory = self.load_memory()
        if not os.path.exists(self.memory_file) and os.path.exists("jarvis_memory.json"):
            try:
                with open("jarvis_memory.json", "r", encoding="utf-8") as f:
                    self.memory = json.load(f)
            except Exception:
                pass

    # ─────────────────────────────────────
    # LOAD MEMORY
    # ─────────────────────────────────────
    def load_memory(self):
        if not os.path.exists(self.memory_file):
            return {
                "user_name": "",
                "preferences": {},
                "conversations": [],
                "notes": []
            }

        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "user_name": "",
                "preferences": {},
                "conversations": [],
                "notes": []
            }

    # ─────────────────────────────────────
    # SAVE MEMORY
    # ─────────────────────────────────────
    def save_memory(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=4)

    # ─────────────────────────────────────
    # SAVE CONVERSATION
    # ─────────────────────────────────────
    def add_conversation(self, user, assistant):
        self.memory["conversations"].append({
            "time": str(datetime.datetime.now()),
            "user": user,
            "assistant": assistant
        })

        # KEEP LAST 50
        self.memory["conversations"] = self.memory["conversations"][-50:]
        self.save_memory()

    # ─────────────────────────────────────
    # SAVE USER NAME
    # ─────────────────────────────────────
    def set_user_name(self, name):
        self.memory["user_name"] = name
        self.save_memory()

    # ─────────────────────────────────────
    # GET USER NAME
    # ─────────────────────────────────────
    def get_user_name(self):
        return self.memory.get("user_name", "")

    # ─────────────────────────────────────
    # SAVE NOTE
    # ─────────────────────────────────────
    def add_note(self, note):
        self.memory["notes"].append(note)
        self.save_memory()

    # ─────────────────────────────────────
    # GET NOTES
    # ─────────────────────────────────────
    def get_notes(self):
        return self.memory["notes"]