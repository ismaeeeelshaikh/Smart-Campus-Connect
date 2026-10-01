"""RAG helpers: source extraction, language detection, and which queries get searched."""
import httpx
import openai
import pytest

from app.services.rag import AssistantBusy, AssistantUnavailable, RAGService, detect_language, finalize_answer

HITS = [
    {"id": "1", "url": "https://www.apsit.edu.in/civil-faculty", "title": "Civil Faculty", "score": 0.9,
     "text": "Civil Faculty\nDr. Mugdha Agarwadkar | department: Civil Engineering | designation: Head of Department (HOD)"},
    {"id": "2", "url": "https://www.apsit.edu.in/tpo", "title": "TPO", "score": 0.8, "text": "TPO\nProf. Sushrut Patankar"},
    {"id": "3", "url": "https://www.apsit.edu.in/sites/default/files/2026-05/FE_Fee.pdf", "title": "FE Fee Structure (PDF)",
     "score": 0.7, "text": "FE Fee Structure Total fees Rs. 1,38,999 for open category"},
    {"id": "4", "url": "", "title": "APSIT ADMISSIONS (file)", "score": 0.6, "text": "DTE Code: 3475"},  # local file
]


@pytest.mark.parametrize("raw, sources, removed", [
    ("The HOD is **Dr. Mugdha**【1】.\n\n**Source:** [Civil Faculty – APSIT](https://www.apsit.edu.in/civil-faculty)", ["Civil Faculty"], "Source"),
    ("TPO is Prof. Patankar.\n\nSources:\n- [TPO](https://www.apsit.edu.in/tpo)\n- [Fake](https://www.apsit.edu.in/made-up)", ["TPO"], "Sources"),
    ("See the [TPO page](https://www.apsit.edu.in/tpo).", ["TPO"], None),
    ("Answer.\n\nSource: https://www.apsit.edu.in/civil-faculty, https://evil.example.com/x", ["Civil Faculty"], "Source"),
    ("प्रमुख **Dr. Mugdha Agarwadkar** आहेत.\n\n**स्रोत:**\n- Civil Faculty page\n- Academic Council page", ["Civil Faculty"], "स्रोत"),
    ("Bhai, first-year ki total fee **Rs. 138,999** hai.", ["FE Fee Structure (PDF)"], None),
    ("The HOD is **Dr. Sushrut Patankar**.", ["TPO"], None),  # name written slightly differently from the page
    ("Fee: **Rs. 1 38 999**", [], None),                     # different digits grouping isn't guessed
    ("DTE code is **3475**.", [], None),               # only in a local file: no chip
    ("Hi! Main sirf APSIT ke baare mein help kar sakta hoon.", [], None),
])
def test_finalize_answer(raw, sources, removed):
    answer = finalize_answer(raw, HITS)
    assert [s["title"] for s in answer.sources] == sources
    assert "【" not in answer.text
    if removed:
        assert removed not in answer.text


def test_trailing_bullet_list_without_label_is_kept():
    assert finalize_answer("Facilities:\n- Library\n- Gym", HITS).text.endswith("- Gym")


@pytest.mark.parametrize("text, language", [
    ("Who is the HOD of Civil?", "english"),
    ("tell me about the main building", "english"),
    ("Civil department ke HOD kaun hai?", "hinglish"),
    ("Bhai first year ki fees kitni hai?", "hinglish"),
    ("सिविल विभाग के प्रमुख कौन हैं?", "devanagari"),
    ("सिव्हिल विभागाचे प्रमुख कोण आहेत?", "devanagari"),
])
def test_detect_language(text, language):
    assert detect_language(text) == language


class RecordingKB:
    def __init__(self):
        self.queries = []

    def search(self, query, k):
        self.queries.append(query)
        return []


class EchoLLM:
    """Pretends to translate: always returns the same English question."""

    async def ainvoke(self, messages):
        class R:
            content = "Who is the Head of Department (HOD) of Civil Engineering?"
        return R()


async def test_devanagari_questions_are_searched_in_english_only():
    kb = RecordingKB()
    rag = RAGService(kb, llm=None, fast_llm=EchoLLM())
    await rag._prepare("सिविल विभाग के प्रमुख कौन हैं?", [])
    assert kb.queries == ["Who is the Head of Department (HOD) of Civil Engineering?"]


async def test_hinglish_questions_are_searched_in_english_and_original():
    kb = RecordingKB()
    rag = RAGService(kb, llm=None, fast_llm=EchoLLM())
    await rag._prepare("Civil department ke HOD kaun hai?", [])
    assert kb.queries == ["Who is the Head of Department (HOD) of Civil Engineering?", "Civil department ke HOD kaun hai?"]


async def test_english_questions_skip_translation_and_follow_ups_add_the_previous_question():
    kb = RecordingKB()
    rag = RAGService(kb, llm=None, fast_llm=None)  # would crash if translation were attempted
    messages, _ = await rag._prepare("What is her qualification?", [("Who is the HOD of Civil?", "Dr. Mugdha Agarwadkar")])
    assert kb.queries == ["What is her qualification?", "Who is the HOD of Civil? What is her qualification?"]
    assert "Answer in English." in messages[-1].content


class FailingLLM:
    def __init__(self, error):
        self.error = error

    async def ainvoke(self, messages):
        raise self.error

    async def astream(self, messages):
        raise self.error
        yield  # makes this an async generator


REQUEST = httpx.Request("POST", "http://llm.local/v1/chat/completions")


@pytest.mark.parametrize("error, expected", [
    (openai.RateLimitError("429", response=httpx.Response(429, request=REQUEST), body=None), AssistantBusy),
    (openai.APIConnectionError(request=REQUEST), AssistantUnavailable),      # server down / unreachable
    (openai.APITimeoutError(request=REQUEST), AssistantUnavailable),
    (openai.InternalServerError("502", response=httpx.Response(502, request=REQUEST), body=None), AssistantUnavailable),
])
async def test_llm_server_errors_become_friendly_errors(error, expected):
    rag = RAGService(RecordingKB(), llm=FailingLLM(error))
    with pytest.raises(expected) as info:
        await rag.answer("Who is the HOD of Civil?")
    assert type(info.value) is expected
    with pytest.raises(expected):
        async for _ in rag.stream("Who is the HOD of Civil?"):
            pass
