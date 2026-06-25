# memory_engine.py
import json
import os
import datetime


class MemoryEngine:

    def __init__(self):
        self.memory_file = "jarvis_memory.json"
        self.memory = self.load_memory()

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
    def add_conversation(self, user, jarvis):
        self.memory["conversations"].append({
            "time": str(datetime.datetime.now()),
            "user": user,
            "jarvis": jarvis
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