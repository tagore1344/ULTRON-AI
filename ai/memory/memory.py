class Memory:

    def __init__(self):

        self.data = {}

    def set(self, key, value):

        self.data[key] = value

    def get(self, key):

        return self.data.get(key)

    def remove(self, key):

        if key in self.data:
            del self.data[key]

    def exists(self, key):

        return key in self.data

    def clear(self):

        self.data.clear()

    def all(self):

        return self.data