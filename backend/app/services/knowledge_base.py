"""Persistent vector knowledge base (Chroma + sentence-transformers).

Every document is stored under a `source` id (e.g. "manual:apsit_admissions.txt", later
"https://www.apsit.edu.in/civil-faculty"). A source is only re-embedded when its content hash
changes, so restarting the backend doesn't rebuild the whole index.
"""
import hashlib
import logging
import math
import re
from collections import Counter
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

COLLECTION = "apsit_kb"
# Bump this when chunking changes, so every source gets re-indexed once
CHUNKER_VERSION = "2"
# BGE models retrieve better when the *query* (not the documents) has this instruction
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
SECTION_RE = re.compile(r"^=+\s*(.+?)\s*=+$")
# Leftovers from AI-assisted scraping, e.g. "[cite_start]" or "[cite: 411, 497, ...]"
CITE_TAG_RE = re.compile(r"\[cite[^\]]*\]")
TOKEN_RE = re.compile(r"[a-z0-9]+")
# Question words that carry no meaning for keyword matching
STOPWORDS = set("""a an and any are about can could do does for from give has have how i in is it me
my of on or please show tell the there this to what whats when where which who whom whose why will with
you your apsit college""".split())

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=150, separators=["\n\n", "\n", ". ", " ", ""]
)


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split on '=== HEADER ===' lines -> [(header, body)]. Text before the first header gets ''."""
    sections, header, lines = [], "", []
    for line in text.splitlines():
        match = SECTION_RE.match(line.strip())
        if match:
            if any(l.strip() for l in lines):
                sections.append((header, "\n".join(lines).strip()))
            header, lines = match.group(1), []
        else:
            lines.append(line)
    if any(l.strip() for l in lines):
        sections.append((header, "\n".join(lines).strip()))
    return sections


def _tokens(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class _KeywordIndex:
    """Small BM25 index. Complements vector search, which is weak on exact terms
    such as "DTE code", "NIRF", subject codes and people's names."""

    def __init__(self, ids: list[str], docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.ids, self.k1, self.b = ids, k1, b
        self.tfs = [Counter(_tokens(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = (sum(self.lens) / len(self.lens)) if docs else 0
        df = Counter(t for tf in self.tfs for t in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, k: int) -> list[str]:
        terms = [t for t in set(_tokens(query)) if t in self.idf]
        scored = []
        for i, tf in enumerate(self.tfs):
            s = sum(
                self.idf[t] * tf[t] * (self.k1 + 1)
                / (tf[t] + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg_len))
                for t in terms if tf[t]
            )
            if s > 0:
                scored.append((s, i))
        return [self.ids[i] for _, i in sorted(scored, reverse=True)[:k]]


def chunk_text(text: str, title: str) -> list[str]:
    """Chunks of ~1000 chars, each prefixed with the document title and its section header,
    so a chunk like '- Prof. X, Assistant Professor' still says which department it belongs to."""
    text = CITE_TAG_RE.sub("", text)
    chunks = []
    for header, body in _split_sections(text):
        prefix = f"{title} > {header}" if header else title
        chunks.extend(f"{prefix}\n{piece}" for piece in _splitter.split_text(body))
    return chunks


class KnowledgeBase:
    def __init__(self, persist_dir: Path, embedding_model: str):
        logger.info(f"Loading embedding model {embedding_model}...")
        try:
            # Use the cached copy without contacting huggingface.co on every start
            self.model = SentenceTransformer(embedding_model, local_files_only=True)
        except Exception:
            self.model = SentenceTransformer(embedding_model)  # first run: download it

        persist_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(persist_dir), settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
        self.refresh_keyword_index()
        logger.info(f"Knowledge base ready: {self.collection.count()} chunks in {persist_dir}")

    def refresh_keyword_index(self):
        """Rebuild the in-memory keyword index and chunk cache. Call after changing sources."""
        everything = self.collection.get(include=["documents", "metadatas"])
        chunks = {
            id_: (doc, meta) for id_, doc, meta in zip(everything["ids"], everything["documents"], everything["metadatas"])
        }
        # One assignment, so a search running in another thread never sees a half-updated pair
        self._index = (chunks, _KeywordIndex(list(chunks), [doc for doc, _ in chunks.values()]))

    # ---- embeddings ----
    def _embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True, batch_size=8).tolist()

    def _embed_query(self, text: str) -> list[float]:
        return self.model.encode(BGE_QUERY_PREFIX + text, normalize_embeddings=True).tolist()

    # ---- writing ----
    def sync_source(self, source: str, title: str, text: str, kind: str, url: str = "") -> str:
        """Add or update one document. Returns 'added', 'updated' or 'unchanged'."""
        content_hash = hashlib.sha256(f"{CHUNKER_VERSION}\n{title}\n{url}\n{text}".encode()).hexdigest()
        existing = self.collection.get(where={"source": source}, limit=1, include=["metadatas"])
        if existing["ids"] and existing["metadatas"][0].get("content_hash") == content_hash:
            return "unchanged"

        self.collection.delete(where={"source": source})
        chunks = chunk_text(text, title)
        if chunks:
            self.collection.add(
                ids=[f"{source}#{i}" for i in range(len(chunks))],
                documents=chunks,
                embeddings=self._embed_documents(chunks),
                metadatas=[
                    {"source": source, "title": title, "url": url, "kind": kind,
                     "content_hash": content_hash, "chunk": i}
                    for i in range(len(chunks))
                ],
            )
        return "updated" if existing["ids"] else "added"

    def remove_source(self, source: str):
        self.collection.delete(where={"source": source})

    def sources(self, kind: str) -> set[str]:
        result = self.collection.get(where={"kind": kind}, include=["metadatas"])
        return {m["source"] for m in result["metadatas"]}

    def sync_folder(self, folder: Path) -> dict[str, int]:
        """Index every .txt file in `folder` (source 'manual:<file name>'); drop files that were deleted."""
        stats = {"added": 0, "updated": 0, "unchanged": 0, "removed": 0}
        current = set()
        for path in sorted(folder.glob("*.txt")):
            source = f"manual:{path.name}"
            current.add(source)
            text = path.read_text(encoding="utf-8-sig")  # -sig strips the BOM some files have
            title, body = _title_and_body(text, path)
            stats[self.sync_source(source, title, body, kind="manual")] += 1
        for source in self.sources("manual") - current:
            self.remove_source(source)
            stats["removed"] += 1
        if stats["added"] or stats["updated"] or stats["removed"]:
            self.refresh_keyword_index()
        return stats

    # ---- reading ----
    def search(self, query: str, k: int = 6) -> list[dict]:
        """Hybrid search: vector (meaning) + keyword (exact terms), merged with reciprocal rank fusion."""
        chunks, keyword = self._index
        total = self.collection.count()
        if total == 0:
            return []
        n = min(k * 2, total)
        vector = self.collection.query(query_embeddings=[self._embed_query(query)], n_results=n, include=[])
        rankings = [vector["ids"][0], keyword.search(query, n)]

        fused: dict[str, float] = {}
        for ranking in rankings:
            for rank, id_ in enumerate(ranking):
                fused[id_] = fused.get(id_, 0.0) + 1 / (60 + rank)
        top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]

        # Chunks added by a sync that's still running aren't in the cache yet: read them directly
        missing = [id_ for id_, _ in top if id_ not in chunks]
        if missing:
            got = self.collection.get(ids=missing, include=["documents", "metadatas"])
            chunks = {**chunks, **{i: (d, m) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}}

        hits = []
        for id_, score in top:
            if id_ not in chunks:  # deleted since the cache was built
                continue
            doc, meta = chunks[id_]
            hits.append({"id": id_, "text": doc, "title": meta["title"], "url": meta.get("url", ""),
                         "kind": meta.get("kind", ""), "source": meta["source"], "score": score})
        return hits


def _title_and_body(text: str, path: Path) -> tuple[str, str]:
    """Use the first line as the title when it's an ALL-CAPS heading, else the file name."""
    lines = text.strip().splitlines()
    first = lines[0].strip() if lines else ""
    if first and first == first.upper() and not SECTION_RE.match(first) and len(first) < 120:
        return first, "\n".join(lines[1:])
    return path.stem.replace("_", " ").title(), text
