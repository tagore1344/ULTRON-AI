# ai/memory/vector_memory.py — Simple vector memory store
import math


def _cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two dict-based sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0

    common = set(vec_a.keys()) & set(vec_b.keys())
    if not common:
        return 0.0

    dot = sum(vec_a[k] * vec_b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


class VectorMemory:
    """Stores text entries with simple vector representations for similarity search."""

    def __init__(self):
        self.entries = []  # list of {"text": str, "vector": dict}

    def _tokenize(self, text):
        """Convert text to a simple term-frequency dict."""
        tokens = text.lower().split()
        freq = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1
        return freq

    def add(self, text):
        """Add a text entry to the vector memory."""
        vector = self._tokenize(text)
        self.entries.append({"text": text, "vector": vector})
        return len(self.entries) - 1

    def search(self, query, top_k=3):
        """Return the top-k most similar entries to the query."""
        query_vector = self._tokenize(query)
        scored = []
        for entry in self.entries:
            score = _cosine_similarity(query_vector, entry["vector"])
            scored.append((score, entry["text"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for score, text in scored[:top_k] if score > 0]

    def size(self):
        """Return the number of stored entries."""
        return len(self.entries)

    def clear(self):
        """Clear all stored entries."""
        self.entries = []