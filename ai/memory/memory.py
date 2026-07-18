import json
import os


class Memory:

    def __init__(self, filename="memory.json"):

        self.filename = filename
        self.data = {}

        self._load()

    def _load(self):

        if os.path.exists(self.filename):

            try:

                with open(self.filename, "r", encoding="utf-8") as f:
                    self.data = json.load(f)

            except Exception:

                self.data = {}

    def _save(self):

        with open(self.filename, "w", encoding="utf-8") as f:

            json.dump(
                self.data,
                f,
                indent=4,
                ensure_ascii=False
            )

    def set(self, key, value):

        self.data[key] = value
        self._save()

    def get(self, key):

        return self.data.get(key)

    def remove(self, key):

        if key in self.data:

            del self.data[key]
            self._save()

    def exists(self, key):

        return key in self.data

    def clear(self):

        self.data.clear()
        self._save()

    def all(self):

        return self.data