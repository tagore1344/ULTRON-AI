from .memory import Memory


class ShortTermMemory:

    def __init__(self):

        self.memory = Memory()

    def remember(self, key, value):

        self.memory.set(key, value)

    def recall(self, key):

        return self.memory.get(key)

    def forget(self, key):

        self.memory.remove(key)

    def exists(self, key):

        return self.memory.exists(key)

    def clear(self):

        self.memory.clear()

    def dump(self):

        return self.memory.all()