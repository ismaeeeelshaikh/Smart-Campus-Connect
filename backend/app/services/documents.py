"""PDFs students upload to a chat: reading, storing and searching them.

Only the text of a PDF is kept (split into chunks), never the file. Uploading only reads and
stores the text, so it takes a second; the chunks' embeddings are computed afterwards in the
background (on a CPU that's about a second per chunk). Until a chunk has its embedding it is
found by keyword search only. Questions in that chat search the PDF next to the college
knowledge base; see RAGService.
"""
import asyncio
import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Optional

import numpy as np
from pypdf import PdfReader
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import async_session
from ..models.chat_document import ChatDocument, ChatDocumentChunk
from .knowledge_base import _KeywordIndex, chunk_text

logger = logging.getLogger(__name__)

# About 100 dense pages. Keeps indexing time and the search per question small.
MAX_CHUNKS = 600
INDEX_BATCH = 16

_tasks: set[asyncio.Task] = set()  # running background indexing (kept so they aren't garbage-collected)


class DocumentError(Exception):
    """A PDF that can't be used. The message is shown to the user."""


@dataclass
class DocumentIndex:
    """The chunks of one uploaded PDF, ready to search."""
    document_id: int
    filename: str
    pages: list[int]
    texts: list[str]
    vectors: np.ndarray  # normalized embeddings of the chunks that have one...
    vector_ids: list[int]  # ...and which chunk each row belongs to
    _keyword: _KeywordIndex = field(init=False, repr=False)

    def __post_init__(self):
        self._keyword = _KeywordIndex([str(i) for i in range(len(self.texts))], self.texts)

    def _hit(self, i: int, score: float) -> dict:
        return {"id": f"upload:{self.document_id}#{i}", "text": self.texts[i], "title": self.filename, "url": "",
                "kind": "upload", "page": self.pages[i], "score": score}

    def first(self, k: int) -> list[dict]:
        """The first k chunks in page order (the whole PDF when it's short)."""
        return [self._hit(i, 1.0) for i in range(min(k, len(self.texts)))]

    def search(self, query: str, query_vector, k: int) -> list[dict]:
        """Hybrid search (vector + keyword, reciprocal rank fusion), like KnowledgeBase.search."""
        n = min(k * 2, len(self.texts))
        rankings = [[int(i) for i in self._keyword.search(query, n)]]
        if query_vector is not None and self.vector_ids:
            query_vector = np.asarray(query_vector, dtype=np.float32)
            if self.vectors.shape[1] == query_vector.shape[0]:  # not if the embedding model changed since
                order = np.argsort(-(self.vectors @ query_vector))[:n]
                rankings.append([self.vector_ids[j] for j in order])
        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1 / (60 + rank)
        top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]
        return [self._hit(i, score) for i, score in top]


# ---- reading a PDF ----

def clean_filename(name: Optional[str]) -> str:
    base = PurePath((name or "").replace("\\", "/")).name
    base = re.sub(r"[\x00-\x1f]", "", base).strip()[:120]
    return base or "document.pdf"


def _clean(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    # Some PDFs (e.g. made from Word text boxes) come out one word per line: join those back into text
    if lines and sum(len(line.split()) for line in lines) / len(lines) < 2:
        return " ".join(lines)
    return "\n".join(lines)


def extract_pages(data: bytes, max_pages: int) -> list[str]:
    """The text of each page. Raises DocumentError for files that can't be used."""
    if b"%PDF-" not in data[:1024]:
        raise DocumentError("This file isn't a PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise DocumentError("This PDF is password-protected. Please upload an unlocked copy.")
        count = len(reader.pages)
    except DocumentError:
        raise
    except Exception:
        raise DocumentError("Could not read this PDF. The file may be damaged.") from None
    if count > max_pages:
        raise DocumentError(f"This PDF has {count} pages; the limit is {max_pages}.")
    pages = []
    for page in reader.pages:
        try:
            pages.append(_clean(page.extract_text() or ""))
        except Exception:
            pages.append("")
    if not any(pages):
        raise DocumentError("This PDF has no selectable text (it may be a scanned image), so it can't be read.")
    return pages


def make_chunks(filename: str, pages: list[str]) -> list[tuple[int, str]]:
    """[(page number, chunk text)]. Each chunk starts with the file name and page, which helps search."""
    chunks = [(number, piece) for number, text in enumerate(pages, 1) if text
              for piece in chunk_text(text, f"{filename}, page {number}")]
    if len(chunks) > MAX_CHUNKS:
        raise DocumentError("This PDF has too much text. Please upload a shorter one (about 100 pages at most).")
    return chunks


# ---- storing ----

async def save_document(db: AsyncSession, session_id: int, filename: str, data: bytes) -> ChatDocument:
    """Read the PDF and store its text for the chat, replacing an earlier PDF. The caller commits,
    then calls start_indexing(document.id, ...)."""
    pages = await asyncio.to_thread(extract_pages, data, settings.upload_max_pages)
    chunks = make_chunks(filename, pages)
    await db.execute(delete(ChatDocument).where(ChatDocument.chat_session_id == session_id))
    document = ChatDocument(chat_session_id=session_id, filename=filename, pages=len(pages))
    document.chunks = [ChatDocumentChunk(position=i, page=page, text=text) for i, (page, text) in enumerate(chunks)]
    db.add(document)
    await db.flush()
    logger.info(f"PDF stored for chat {session_id}: {len(pages)} pages, {len(chunks)} chunks")
    return document


async def remove_document(db: AsyncSession, session_id: int) -> bool:
    """Delete the chat's PDF (its chunks go with it). The caller commits."""
    result = await db.execute(delete(ChatDocument).where(ChatDocument.chat_session_id == session_id))
    return result.rowcount > 0


# ---- background indexing ----

async def index_document(document_id: int, embedder):
    """Embed the document's chunks that have no embedding yet, a few at a time. Stops by itself when
    the PDF is removed or replaced meanwhile. `embedder`: the knowledge base (same model as questions)."""
    try:
        while True:
            async with async_session() as db:
                rows = (await db.execute(
                    select(ChatDocumentChunk.id, ChatDocumentChunk.text)
                    .where(ChatDocumentChunk.document_id == document_id, ChatDocumentChunk.embedding.is_(None))
                    .order_by(ChatDocumentChunk.position)
                    .limit(INDEX_BATCH)
                )).all()
            if not rows:
                return
            vectors = await asyncio.to_thread(embedder.embed_documents, [r.text for r in rows])
            async with async_session() as db:
                for row, vector in zip(rows, vectors, strict=True):
                    await db.execute(update(ChatDocumentChunk).where(ChatDocumentChunk.id == row.id)
                                     .values(embedding=np.asarray(vector, dtype=np.float32).tobytes()))
                await db.commit()
    except Exception:
        logger.exception(f"Indexing PDF {document_id} failed; it stays searchable by keywords")


def start_indexing(document_id: int, embedder):
    task = asyncio.create_task(index_document(document_id, embedder))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def resume_indexing(embedder):
    """At startup: finish PDFs whose indexing was cut off by a restart."""
    async with async_session() as db:
        pending = (await db.execute(
            select(ChatDocumentChunk.document_id).where(ChatDocumentChunk.embedding.is_(None)).distinct()
        )).scalars().all()
    for document_id in pending:
        start_indexing(document_id, embedder)
    if pending:
        logger.info(f"Resumed indexing of {len(pending)} uploaded PDF(s)")


async def wait_for_indexing():
    """For tests: wait until all background indexing is done."""
    while _tasks:
        await asyncio.gather(*list(_tasks), return_exceptions=True)


# ---- loading for a question ----

async def load_index(db: AsyncSession, session_id: int) -> Optional[DocumentIndex]:
    """The chat's PDF ready to search, or None if it has none."""
    document = (await db.execute(
        select(ChatDocument.id, ChatDocument.filename).where(ChatDocument.chat_session_id == session_id)
    )).first()
    if document is None:
        return None
    rows = (await db.execute(
        select(ChatDocumentChunk.page, ChatDocumentChunk.text, ChatDocumentChunk.embedding)
        .where(ChatDocumentChunk.document_id == document.id)
        .order_by(ChatDocumentChunk.position)
    )).all()
    vector_ids = [i for i, r in enumerate(rows) if r.embedding is not None]
    vectors = (np.vstack([np.frombuffer(rows[i].embedding, dtype=np.float32) for i in vector_ids])
               if vector_ids else np.zeros((0, 0), dtype=np.float32))
    return DocumentIndex(document.id, document.filename, [r.page for r in rows], [r.text for r in rows],
                         vectors, vector_ids)
