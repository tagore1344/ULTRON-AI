from .memory import Memory


class LongTermMemory:

    def __init__(self):

        self.memory = Memory()

    def save(self, key, value):

        self.memory.set(key, value)

    def load(self, key):

        return self.memory.get(key)

    def delete(self, key):

        self.memory.remove(key)

    def exists(self, key):

        return self.memory.exists(key)

    def clear(self):

        self.memory.clear()

    def dump(self):

        return self.memory.all()