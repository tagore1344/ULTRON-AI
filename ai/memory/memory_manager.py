from .short_term_memory import ShortTermMemory
from .long_term_memory import LongTermMemory


class MemoryManager:

    def __init__(self):

        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    # ---------- Short Term ----------

    def remember(self, key, value):

        self.short_term.remember(key, value)

    def recall(self, key):

        return self.short_term.recall(key)

    def forget(self, key):

        self.short_term.forget(key)

    # ---------- Long Term ----------

    def save(self, key, value):

        self.long_term.save(key, value)

    def load(self, key):

        return self.long_term.load(key)

    def delete(self, key):

        self.long_term.delete(key)

    # ---------- Utilities ----------

    def clear_short_memory(self):

        self.short_term.clear()

    def clear_long_memory(self):

        self.long_term.clear()

    def dump_short_memory(self):

        return self.short_term.dump()

    def dump_long_memory(self):

        return self.long_term.dump()