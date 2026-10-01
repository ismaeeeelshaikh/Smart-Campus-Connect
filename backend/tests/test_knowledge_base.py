"""Knowledge base: chunking, keyword search, and incremental sync (with a fake embedding model)."""
import pytest

from app.services.knowledge_base import KnowledgeBase, _KeywordIndex, chunk_text
from helpers import FakeEmbedder


def test_chunks_keep_title_and_section_and_drop_cite_tags():
    text = "=== CIVIL ENGINEERING ===\nThe HOD is Dr. X. [cite_start]Labs are new.[cite: 12, 13]\n=== FEES ===\nFees are Rs. 1,000."
    chunks = chunk_text(text, "APSIT INFO")
    assert chunks[0].startswith("APSIT INFO > CIVIL ENGINEERING\n") and "Dr. X" in chunks[0]
    assert chunks[1].startswith("APSIT INFO > FEES\n")
    assert all("[cite" not in c for c in chunks)


def test_keyword_index_finds_exact_terms():
    index = _KeywordIndex(["a", "b", "c"], ["DTE Code: 3475", "Library rules and timings", "Placement statistics"])
    assert index.search("What is the DTE code?", 2) == ["a"]
    assert index.search("what is", 2) == []  # only stopwords: no keyword match


@pytest.fixture
def kb(tmp_path):
    return KnowledgeBase(tmp_path / "chroma", "fake-model", model=FakeEmbedder())


def test_sync_only_reembeds_changed_sources(kb):
    url = "https://www.apsit.edu.in/tpo"
    assert kb.sync_source(url, "TPO", "Prof. Sushrut Patankar heads training and placement.", "web", url) == "added"
    assert kb.sync_source(url, "TPO", "Prof. Sushrut Patankar heads training and placement.", "web", url) == "unchanged"
    assert kb.sync_source(url, "TPO", "Prof. Test Person heads training and placement.", "web", url) == "updated"
    assert kb.sources("web") == {url}
    kb.remove_source(url)
    assert kb.sources("web") == set()


def test_search_hybrid_and_new_chunks_before_refresh(kb):
    kb.sync_source("manual:a.txt", "ADMISSIONS", "DTE Code: 3475. Admissions open in June.", "manual")
    kb.sync_source("manual:b.txt", "LIBRARY", "Library rules: books can be kept for 14 days.", "manual")
    kb.refresh_keyword_index()
    assert kb.search("What is the DTE code?", 1)[0]["source"] == "manual:a.txt"

    # added after the last refresh: still found (read straight from the vector store)
    kb.sync_source("https://www.apsit.edu.in/sports", "Sports", "Cricket ground and gymnasium on campus.", "web",
                   "https://www.apsit.edu.in/sports")
    hits = kb.search("cricket ground gymnasium", 3)
    assert any(h["source"] == "https://www.apsit.edu.in/sports" for h in hits)


def test_sync_folder_adds_updates_and_removes_files(kb, tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "a.txt").write_text("APSIT GENERAL\n=== LINKS ===\nMoodle: https://elearn.apsit.edu.in", encoding="utf-8")
    (folder / "b.txt").write_text("Some notes about the library.", encoding="utf-8")
    assert kb.sync_folder(folder) == {"added": 2, "updated": 0, "unchanged": 0, "removed": 0}
    assert kb.sync_folder(folder) == {"added": 0, "updated": 0, "unchanged": 2, "removed": 0}

    (folder / "b.txt").unlink()
    (folder / "a.txt").write_text("APSIT GENERAL\n=== LINKS ===\nMoodle moved: https://moodle.apsit.edu.in", encoding="utf-8")
    assert kb.sync_folder(folder) == {"added": 0, "updated": 1, "unchanged": 0, "removed": 1}
    assert kb.sources("manual") == {"manual:a.txt"}
