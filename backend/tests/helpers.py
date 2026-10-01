"""Shared test helpers: a stub for the AI, a fake embedding model, a PDF maker and an SSE parser."""
import json
import zlib

import numpy as np

from app.services.rag import Answer

STUB_SOURCES = [{"title": "Civil Faculty", "url": "https://www.apsit.edu.in/civil-faculty"}]


class FakeKB:
    """Only the embedding part of the knowledge base (what uploaded PDFs need), with the fake model."""

    def __init__(self):
        self.model = FakeEmbedder()

    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()

    def embed_query(self, text):
        return self.model.encode(text).tolist()


class FakeRag:
    """Stands in for RAGService: answers instantly and records what it was given."""

    def __init__(self):
        self.kb = FakeKB()
        self.last_question = None
        self.last_history = None
        self.last_document = None

    def _text(self, question, history, document):
        self.last_question, self.last_history, self.last_document = question, history or [], document
        return f"stub answer to: {question} (history turns: {len(self.last_history)})"

    async def answer(self, question, history=None, document=None):
        return Answer(self._text(question, history, document), STUB_SOURCES)

    async def stream(self, question, history=None, document=None):
        text = self._text(question, history, document)
        for i in range(0, len(text), 7):
            yield text[i:i + 7]
        yield Answer(text, STUB_SOURCES)


def make_pdf(pages: list[str]) -> bytes:
    """A small valid PDF with one line of text per page (Helvetica). An empty string makes a blank page."""
    page_ids = [4 + 2 * i for i in range(len(pages))]
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(pages)} >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_id, text in zip(page_ids, pages, strict=True):
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                       f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>")
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET" if text else ""
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


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
