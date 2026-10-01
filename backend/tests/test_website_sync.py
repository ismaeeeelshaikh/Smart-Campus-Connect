"""Website sync: incremental updates and the safety rules for removing pages (crawler is faked)."""
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.database import async_session
from app.models import CrawledPage, CrawlRun
from app.services import website_sync
from app.services.crawler import Page
from app.services.knowledge_base import KnowledgeBase
from app.services.rag import set_rag_service
from helpers import FakeEmbedder

BASE = "https://www.apsit.edu.in"


@pytest.fixture
def kb(tmp_path):
    kb = KnowledgeBase(tmp_path / "chroma", "fake-model", model=FakeEmbedder())
    set_rag_service(SimpleNamespace(kb=kb))  # website_sync uses get_rag_service().kb
    return kb


def fake_site(monkeypatch, pages: dict[str, str], not_found=(), hit_page_limit=False):
    """Make website_sync's crawl() return these pages (path -> text)."""
    async def crawl(*, result, **_):
        for path, text in pages.items():
            result.pages_ok += 1
            yield Page(BASE + path, path.strip("/").title(), text, "web")
        result.not_found.extend(BASE + p for p in not_found)
        result.hit_page_limit = hit_page_limit
    monkeypatch.setattr(website_sync, "crawl", crawl)


async def runs():
    async with async_session() as db:
        return (await db.execute(select(CrawlRun).order_by(CrawlRun.id))).scalars().all()


async def test_incremental_sync_and_safe_removal(kb, monkeypatch):
    five = {f"/page{i}": f"Text of page {i}." for i in range(5)}
    fake_site(monkeypatch, five)
    await website_sync.run_sync("test")
    first = (await runs())[-1]
    assert (first.status, first.pages_added, first.pages_removed) == ("success", 5, 0)

    # page0 changed, page4 gone: 4 of 5 pages seen (>= 80%), so page4 is removed
    changed = {**{p: t for p, t in five.items() if p != "/page4"}, "/page0": "New text of page 0."}
    fake_site(monkeypatch, changed)
    await website_sync.run_sync("test")
    second = (await runs())[-1]
    assert (second.pages_updated, second.pages_unchanged, second.pages_removed) == (1, 3, 1)
    assert BASE + "/page4" not in kb.sources("web")
    async with async_session() as db:
        page4 = (await db.execute(select(CrawledPage).where(CrawledPage.url == BASE + "/page4"))).scalar_one()
    assert page4.status == "removed"


async def test_incomplete_crawl_removes_nothing(kb, monkeypatch):
    fake_site(monkeypatch, {f"/page{i}": f"Text {i}." for i in range(5)})
    await website_sync.run_sync("test")
    fake_site(monkeypatch, {"/page0": "Text 0."})  # e.g. the network failed half way
    await website_sync.run_sync("test")
    last = (await runs())[-1]
    assert last.pages_removed == 0 and "kept" in last.error
    assert len(kb.sources("web")) == 5


async def test_deleted_pages_are_removed_even_when_the_crawl_hits_the_limit(kb, monkeypatch):
    fake_site(monkeypatch, {"/a": "A.", "/b": "B."})
    await website_sync.run_sync("test")
    fake_site(monkeypatch, {"/a": "A."}, not_found=["/b"], hit_page_limit=True)
    await website_sync.run_sync("test")
    assert kb.sources("web") == {BASE + "/a"}


async def test_unreachable_website_is_a_failed_run(kb, monkeypatch):
    fake_site(monkeypatch, {})
    await website_sync.run_sync("test")
    assert (await runs())[-1].status == "failed"


async def test_single_page_sync(kb, monkeypatch):
    async def fetch(url):
        return (200, Page(url, "TPO", "Prof. Sushrut Patankar", "web")) if url.endswith("/tpo") else (404, None)
    monkeypatch.setattr(website_sync, "fetch_single", fetch)
    assert (await website_sync.sync_single_page(BASE + "/tpo"))["status"] == "added"
    assert (await website_sync.sync_single_page(BASE + "/tpo"))["status"] == "unchanged"
    assert (await website_sync.sync_single_page(BASE + "/gone"))["status"] == "removed"
    with pytest.raises(website_sync.InvalidPageUrl):
        await website_sync.sync_single_page("https://evil.example.com/")
