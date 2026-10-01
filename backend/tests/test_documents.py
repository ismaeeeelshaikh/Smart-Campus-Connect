"""PDF upload in chats: upload, ask, replace, remove, limits, privacy, and how the PDF is searched."""
import numpy as np
from sqlalchemy import func, select

from app import main
from app.config import settings
from app.database import async_session
from app.models import ChatDocument, ChatDocumentChunk
from app.services.documents import DocumentIndex, make_chunks
from app.services.rag import RAGService, finalize_answer
from helpers import FakeKB, make_pdf, parse_sse

NOTICE = make_pdf([
    "Mid-term examinations for SE students start on 12 March 2027 in Room 401.",
    "Results will be announced on 30 April 2027 on the notice board.",
])


def pdf_file(content=NOTICE, name="exam-notice.pdf"):
    return {"file": (name, content, "application/pdf")}


async def start_with_pdf(client, headers, **kwargs):
    r = await client.post("/chat-sessions/document", files=pdf_file(**kwargs), headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def counts():
    async with async_session() as db:
        return (await db.scalar(select(func.count(ChatDocument.id))),
                await db.scalar(select(func.count(ChatDocumentChunk.id))))


async def test_start_a_chat_with_a_pdf_and_ask_about_it(client, auth_headers, fake_rag):
    data = await start_with_pdf(client, auth_headers)
    sid = data["session"]["id"]
    assert data["session"]["title"] == "exam-notice.pdf" and data["session"]["has_document"] is True
    assert data["document"]["filename"] == "exam-notice.pdf" and data["document"]["pages"] == 2

    # listed even before the first question, and the detail shows the PDF
    sessions = (await client.get("/chat-sessions", headers=auth_headers)).json()["sessions"]
    assert [(s["id"], s["has_document"]) for s in sessions] == [(sid, True)]
    detail = (await client.get(f"/chat-sessions/{sid}", headers=auth_headers)).json()
    assert detail["document"]["filename"] == "exam-notice.pdf" and detail["messages"] == []

    r = await client.post(f"/chat-sessions/{sid}/messages/stream", json={"question": "When do the exams start?"}, headers=auth_headers)
    assert parse_sse(r.text)[-1][0] == "done"
    document = fake_rag.last_document
    assert document is not None and document.filename == "exam-notice.pdf" and document.pages == [1, 2]
    # the PDF's chunks are searchable with the same embedding model as the knowledge base
    hits = document.search("results announced", FakeKB().embed_query("results announced"), k=1)
    assert hits[0]["page"] == 2 and hits[0]["kind"] == "upload"

    # the non-streaming endpoint gets the PDF too
    await client.post(f"/chat-sessions/{sid}/messages", json={"question": "Which room?"}, headers=auth_headers)
    assert fake_rag.last_document.filename == "exam-notice.pdf"


async def test_attach_replace_and_remove(client, auth_headers, fake_rag):
    sid = (await client.post("/chat-sessions/start", json={"question": "Hi"}, headers=auth_headers)).json()["session"]["id"]

    r = await client.put(f"/chat-sessions/{sid}/document", files=pdf_file(), headers=auth_headers)
    assert r.status_code == 200 and r.json()["pages"] == 2
    r = await client.put(f"/chat-sessions/{sid}/document",
                         files=pdf_file(make_pdf(["Timetable: Maths on Monday."]), "timetable.pdf"), headers=auth_headers)
    assert r.json()["filename"] == "timetable.pdf"
    assert await counts() == (1, 1)  # the old PDF and its chunks are gone

    await client.post(f"/chat-sessions/{sid}/messages", json={"question": "When is Maths?"}, headers=auth_headers)
    assert fake_rag.last_document.texts[0].endswith("Timetable: Maths on Monday.")

    assert (await client.delete(f"/chat-sessions/{sid}/document", headers=auth_headers)).status_code == 200
    assert (await client.delete(f"/chat-sessions/{sid}/document", headers=auth_headers)).status_code == 404
    assert (await client.get(f"/chat-sessions/{sid}", headers=auth_headers)).json()["document"] is None
    await client.post(f"/chat-sessions/{sid}/messages", json={"question": "And now?"}, headers=auth_headers)
    assert fake_rag.last_document is None


async def test_deleting_the_chat_deletes_its_pdf(client, auth_headers):
    sid = (await start_with_pdf(client, auth_headers))["session"]["id"]
    assert await counts() == (1, 2)
    assert (await client.delete(f"/chat-sessions/{sid}", headers=auth_headers)).status_code == 200
    assert await counts() == (0, 0)


async def test_files_that_cannot_be_used(client, auth_headers, monkeypatch):
    async def upload(content, name="x.pdf"):
        r = await client.post("/chat-sessions/document", files=pdf_file(content, name), headers=auth_headers)
        return r.status_code, r.json()["detail"]

    assert await upload(b"just some text", "notes.txt") == (400, "This file isn't a PDF.")
    status, detail = await upload(make_pdf(["", ""]))
    assert status == 400 and "no selectable text" in detail

    monkeypatch.setattr(settings, "upload_max_pages", 2)
    status, detail = await upload(make_pdf(["a", "b", "c"]))
    assert status == 400 and "3 pages; the limit is 2" in detail

    monkeypatch.setattr(settings, "upload_max_mb", 0)
    status, detail = await upload(NOTICE)
    assert status == 413 and "too large" in detail

    monkeypatch.setattr(main, "MAX_REQUEST_BYTES", 100)  # refused before the body is read
    r = await client.post("/chat-sessions/document", files=pdf_file(), headers=auth_headers)
    assert r.status_code == 413

    assert await counts() == (0, 0)
    assert (await client.get("/chat-sessions", headers=auth_headers)).json()["sessions"] == []  # no empty chats left


def test_text_cleanup():
    from app.services.documents import _clean
    # one word per line (PDFs made from Word text boxes) is joined back into sentences
    assert _clean("Event\nVenue:\nLab\n307,\n308\n") == "Event Venue: Lab 307, 308"
    # normal lines (a schedule table) keep their line breaks; extra spaces and empty lines go
    assert _clean("1  Last Date of Submitting\n\n2 Display of Merit list 09-09-2026") == \
        "1 Last Date of Submitting\n2 Display of Merit list 09-09-2026"


async def test_pdfs_are_private_and_need_login(client, auth_headers, create_user, login):
    sid = (await start_with_pdf(client, auth_headers))["session"]["id"]
    await create_user(email="other@apsit.edu.in")
    other = await login("other@apsit.edu.in")

    assert (await client.put(f"/chat-sessions/{sid}/document", files=pdf_file(), headers=other)).status_code == 404
    assert (await client.delete(f"/chat-sessions/{sid}/document", headers=other)).status_code == 404
    assert (await client.get(f"/chat-sessions/{sid}", headers=other)).status_code == 404
    assert (await client.post("/chat-sessions/document", files=pdf_file())).status_code in (401, 403)
    assert await counts() == (1, 2)


async def test_upload_rate_limit(client, auth_headers):
    for _ in range(20):
        await client.post("/chat-sessions/document", files=pdf_file(b"not a pdf"), headers=auth_headers)
    r = await client.post("/chat-sessions/document", files=pdf_file(), headers=auth_headers)
    assert r.status_code == 429


# ---- how the PDF is used for answers ----

class KB(FakeKB):
    """Knowledge base stub: records searches and returns one website chunk."""

    def __init__(self):
        super().__init__()
        self.queries = []

    def search(self, query, k):
        self.queries.append(query)
        return [{"id": "web#1", "text": "APSIT exam cell: exams@apsit.edu.in", "title": "Exam Cell",
                 "url": "https://www.apsit.edu.in/exam-cell", "kind": "web", "score": 0.5}][:k]


def make_index(pages, indexed=None):
    """A DocumentIndex for these page texts; `indexed`: which chunks already have embeddings (default all)."""
    chunks = make_chunks("exam-notice.pdf", pages)
    indexed = list(range(len(chunks))) if indexed is None else indexed
    vectors = np.asarray(FakeKB().embed_documents([chunks[i][1] for i in indexed]), dtype=np.float32)
    return DocumentIndex(7, "exam-notice.pdf", [p for p, _ in chunks], [t for _, t in chunks],
                         vectors if indexed else np.zeros((0, 0), dtype=np.float32), indexed)


async def test_a_short_pdf_goes_into_the_context_whole():
    kb = KB()
    kb.embed_query = None  # a short PDF needs no search, so no query embedding
    rag = RAGService(kb, llm=None, fast_llm=None)
    index = make_index(["Mid-term examinations start on 12 March 2027 in Room 401.", "Results on 30 April 2027."])
    messages, hits = await rag._prepare("Summarize this PDF", [], index)
    assert [(h["kind"], h.get("page")) for h in hits] == [("upload", 1), ("upload", 2), ("web", None)]
    context = messages[-1].content
    assert "(PDF uploaded by the user: exam-notice.pdf, page 1)" in context
    assert context.index("exam-notice.pdf, page 1") < context.index("official APSIT website page")


async def test_a_long_pdf_is_searched_even_before_it_is_indexed():
    pages = [f"Chapter {n}: general information about topic number {n}." for n in range(1, 9)]
    pages[6] = "Chapter 7: the grievance committee meets every Friday in Room 12."
    rag = RAGService(KB(), llm=None, fast_llm=None)

    _, hits = await rag._prepare("When does the grievance committee meet?", [], make_index(pages, indexed=[]))
    assert hits[0]["page"] == 7  # found by keywords, no embeddings yet

    _, hits = await rag._prepare("When does the grievance committee meet?", [], make_index(pages))
    assert hits[0]["page"] == 7  # keywords + vectors

    _, hits = await rag._prepare("Give me an overview", [], make_index(pages, indexed=[]))
    assert [h.get("page") for h in hits if h["kind"] == "upload"] == [1, 2, 3, 4]  # nothing matched: the beginning


async def test_uploaded_pdfs_are_indexed_in_the_background(client, auth_headers):
    from app.services.documents import wait_for_indexing
    await start_with_pdf(client, auth_headers)
    await wait_for_indexing()
    async with async_session() as db:
        missing = await db.scalar(select(func.count(ChatDocumentChunk.id)).where(ChatDocumentChunk.embedding.is_(None)))
    assert missing == 0


async def test_indexing_cut_off_by_a_restart_is_resumed(client, auth_headers):
    from app.services.documents import resume_indexing, wait_for_indexing
    sid = (await start_with_pdf(client, auth_headers))["session"]["id"]
    await wait_for_indexing()
    async with async_session() as db:  # as if the backend stopped before indexing
        await db.execute(ChatDocumentChunk.__table__.update().values(embedding=None))
        await db.commit()

    await resume_indexing(FakeKB())
    await wait_for_indexing()
    async with async_session() as db:
        rows = (await db.execute(select(ChatDocumentChunk.embedding))).scalars().all()
    assert len(rows) == 2 and all(rows)
    assert (await client.get(f"/chat-sessions/{sid}", headers=auth_headers)).status_code == 200


async def test_pdf_pages_used_in_the_answer_become_sources():
    hits = [
        {"id": "upload:7#0", "text": "Mid-term examinations start on 12 March 2027 in Room 401.", "title": "exam-notice.pdf",
         "url": "", "kind": "upload", "page": 1, "score": 0.9},
        {"id": "upload:7#1", "text": "Results on 30 April 2027.", "title": "exam-notice.pdf",
         "url": "", "kind": "upload", "page": 2, "score": 0.8},
    ]
    answer = finalize_answer("The exams start on **12 March 2027** in Room **401** (page 1).", hits)
    assert answer.sources == [{"title": "exam-notice.pdf · page 1", "url": ""}]
    assert finalize_answer("I could not find that in the PDF.", hits).sources == []

    # the date is rewritten in words, but the time is kept as in the PDF
    schedule = [{"id": "upload:8#0", "text": "4 Display of Final Merit List 09-09-2026 05:00 PM", "title": "schedule.pdf",
                 "url": "", "kind": "upload", "page": 1, "score": 0.9},
                {"id": "upload:8#1", "text": "Admission office open 10:00 AM to 04:00 PM", "title": "schedule.pdf",
                 "url": "", "kind": "upload", "page": 2, "score": 0.8}]
    answer = finalize_answer("The Final Merit List will be displayed on **09 September 2026 at 05:00 PM**.", schedule)
    assert answer.sources == [{"title": "schedule.pdf · page 1", "url": ""}]

    # in a PDF chat, a website page that only shares a fact isn't guessed as a source; a cited one is kept
    web = {"id": "web#1", "text": "Bootcamp sessions ran 10:00 AM to 04:00 PM", "title": "Web dev report",
           "url": "https://www.apsit.edu.in/web-dev.pdf", "kind": "pdf", "score": 0.7}
    answer = finalize_answer("The office is open **10:00 AM to 04:00 PM**.", schedule + [web])
    assert answer.sources == [{"title": "schedule.pdf · page 2", "url": ""}]
    answer = finalize_answer("Open 10:00 AM.\n\nSource: [Web dev report](https://www.apsit.edu.in/web-dev.pdf)", schedule + [web])
    assert answer.sources == [{"title": "Web dev report", "url": "https://www.apsit.edu.in/web-dev.pdf"},
                              {"title": "schedule.pdf · page 2", "url": ""}]
