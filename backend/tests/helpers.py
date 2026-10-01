"""Shared test helpers: a stub for the AI, a fake embedding model, and an SSE parser."""
import json
import zlib

import numpy as np

from app.services.rag import Answer

STUB_SOURCES = [{"title": "Civil Faculty", "url": "https://www.apsit.edu.in/civil-faculty"}]


class FakeRag:
    """Stands in for RAGService: answers instantly and records the history it was given."""

    def __init__(self):
        self.last_question = None
        self.last_history = None

    def _text(self, question, history):
        self.last_question, self.last_history = question, history or []
        return f"stub answer to: {question} (history turns: {len(self.last_history)})"

    async def answer(self, question, history=None):
        return Answer(self._text(question, history), STUB_SOURCES)

    async def stream(self, question, history=None):
        text = self._text(question, history)
        for i in range(0, len(text), 7):
            yield text[i:i + 7]
        yield Answer(text, STUB_SOURCES)


class FakeEmbedder:
    """Tiny bag-of-words "embedding" with SentenceTransformer's encode() interface (no torch needed)."""

    DIM = 64

    def encode(self, texts, normalize_embeddings=True, batch_size=8):
        single = isinstance(texts, str)
        vectors = []
        for text in [texts] if single else texts:
            v = np.zeros(self.DIM)
            for word in text.lower().split():
                v[zlib.crc32(word.encode()) % self.DIM] += 1
            vectors.append(v / (np.linalg.norm(v) or 1))
        return np.array(vectors[0] if single else vectors)


def parse_sse(body: str) -> list[tuple[str, dict]]:
    """[(event, data), ...] from a text/event-stream body."""
    events = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        event, data = "message", []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if data:
            events.append((event, json.loads("\n".join(data))))
    return events
