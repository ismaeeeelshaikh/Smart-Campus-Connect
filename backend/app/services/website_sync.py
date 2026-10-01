"""Keeps the knowledge base in sync with https://www.apsit.edu.in.

A sync crawls the site, re-indexes only the pages whose content changed, and removes pages that
were deleted. It runs on a schedule (CRAWL_INTERVAL_HOURS) and when an admin presses "Refresh".
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, select, update

from ..config import settings
from ..database import async_session
from ..models.website import CrawledPage, CrawlRun
from .crawler import BASE_URL, CrawlResult, crawl, fetch_single, normalize_url
from .email import send_admin_alert
from .rag import get_rag_service

logger = logging.getLogger(__name__)

WEB_KINDS = ("web", "pdf")
# Only remove pages that weren't visited if this crawl reached at least this share of the
# previous one; otherwise a network problem could wipe most of the knowledge base.
MIN_COMPLETE_RATIO = 0.8
# A failed sync is emailed to the admins at most this often (the schedule retries every 10 minutes,
# so a long website outage would otherwise send an email every 10 minutes).
ALERT_EVERY = timedelta(hours=24)
_last_alert: Optional[datetime] = None

_lock = asyncio.Lock()
_tasks: set[asyncio.Task] = set()  # keep references so background tasks aren't garbage-collected


class SyncAlreadyRunning(Exception):
    pass


def is_running() -> bool:
    return _lock.locked()


def start_in_background(triggered_by: str) -> None:
    """Start a sync without waiting for it. Raises SyncAlreadyRunning if one is in progress."""
    if is_running():
        raise SyncAlreadyRunning()
    task = asyncio.create_task(_run_logged(triggered_by))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _run_logged(triggered_by: str):
    try:
        await run_sync(triggered_by)
    except SyncAlreadyRunning:
        pass
    except Exception:
        logger.exception("Website sync crashed")


async def run_sync(triggered_by: str) -> int:
    """Crawl the website and update the knowledge base. Returns the CrawlRun id."""
    if is_running():
        raise SyncAlreadyRunning()
    async with _lock:
        kb = get_rag_service().kb
        async with async_session() as db:
            previous = (await db.execute(
                select(CrawlRun).where(CrawlRun.status == "success").order_by(desc(CrawlRun.finished_at)).limit(1)
            )).scalar_one_or_none()
            run = CrawlRun(triggered_by=triggered_by, status="running")
            db.add(run)
            await db.commit()
            logger.info(f"Website sync #{run.id} started ({triggered_by})")

            result = CrawlResult()
            seen: set[str] = set()
            try:
                async for page in crawl(
                    max_pages=settings.crawl_max_pages,
                    delay=settings.crawl_delay_seconds,
                    include_pdfs=settings.crawl_include_pdfs,
                    max_pdfs=settings.crawl_max_pdfs,
                    result=result,
                ):
                    seen.add(page.url)
                    status = await asyncio.to_thread(
                        kb.sync_source, page.url, page.title, page.text, page.kind, page.url
                    )
                    await _record_page(db, page.url, page.title, page.kind, changed=status != "unchanged")
                    run.pages_seen += 1
                    setattr(run, f"pages_{status}", getattr(run, f"pages_{status}") + 1)
                    if run.pages_seen % 10 == 0:
                        await db.commit()  # lets the admin status endpoint show progress

                if run.pages_seen == 0:
                    raise RuntimeError("Could not read any page from the website (is it down or blocking us?)")

                # ---- remove deleted pages ----
                to_remove = set(result.not_found)
                complete = not result.hit_page_limit and (
                    previous is None or run.pages_seen >= MIN_COMPLETE_RATIO * previous.pages_seen
                )
                indexed: set[str] = set()
                for kind in WEB_KINDS:
                    indexed |= await asyncio.to_thread(kb.sources, kind)
                if complete:
                    unseen_web = {s for s in indexed - seen if not s.lower().endswith(".pdf")}
                    to_remove |= unseen_web
                # PDFs: remove if no crawled page links to them any more (not just "over the PDF limit")
                if complete and settings.crawl_include_pdfs:
                    to_remove |= {s for s in indexed if s.lower().endswith(".pdf") and s not in result.pdf_links}
                to_remove &= indexed
                for source in to_remove:
                    await asyncio.to_thread(kb.remove_source, source)
                if to_remove:
                    await db.execute(update(CrawledPage).where(CrawledPage.url.in_(to_remove)).values(status="removed"))
                run.pages_removed = len(to_remove)
                run.pages_failed = len(result.failed)
                if result.failed:
                    logger.warning(f"Website sync #{run.id}: {len(result.failed)} URLs failed, e.g. {result.failed[:10]}")
                run.status = "success"
                if not complete:
                    run.error = ("Crawl stopped early (page limit or fewer pages than last time), "
                                 "so pages that weren't visited were kept.")
            except Exception as e:
                logger.exception(f"Website sync #{run.id} failed")
                run.status = "failed"
                run.error = f"{type(e).__name__}: {e}"[:1000]
            finally:
                await asyncio.to_thread(kb.refresh_keyword_index)
                run.finished_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(
                    f"Website sync #{run.id} {run.status}: seen {run.pages_seen}, added {run.pages_added}, "
                    f"updated {run.pages_updated}, unchanged {run.pages_unchanged}, removed {run.pages_removed}, "
                    f"failed {run.pages_failed}"
                )
            if run.status == "failed":
                await _alert_admins(run)
            return run.id


async def _alert_admins(run: CrawlRun):
    """Email the admins that a sync failed (at most once per ALERT_EVERY)."""
    global _last_alert
    now = datetime.now(timezone.utc)
    if not settings.admin_emails() or (_last_alert and now - _last_alert < ALERT_EVERY):
        return
    _last_alert = now
    try:
        await send_admin_alert(
            "Website sync failed",
            f"Website sync #{run.id} ({run.triggered_by}) failed:\n\n{run.error}\n\n"
            "The chatbot keeps answering from the last successful sync. The sync is retried "
            "automatically; you can also start one from the Website sync panel. "
            "(At most one such email is sent per day.)",
        )
    except Exception:
        logger.warning("Could not email the admins about the failed sync", exc_info=True)


_single_lock = asyncio.Lock()


class InvalidPageUrl(ValueError):
    pass


async def sync_single_page(url: str) -> dict:
    """Re-read one page (or PDF) right now, e.g. just after a staff member edited it.
    Works even while a full sync is running. Returns {"url", "title", "status"}."""
    normalized = normalize_url(url, BASE_URL + "/")
    if normalized is None:
        raise InvalidPageUrl("Please give a page or PDF link on https://www.apsit.edu.in")
    kb = get_rag_service().kb
    async with _single_lock:
        http_status, page = await fetch_single(normalized)
        if http_status is None:
            raise RuntimeError("Could not reach the website. Please try again.")
        async with async_session() as db:
            if page is None:
                # Deleted (404) or no usable text any more: take it out of the knowledge base
                await asyncio.to_thread(kb.remove_source, normalized)
                await db.execute(update(CrawledPage).where(CrawledPage.url == normalized).values(status="removed"))
                await db.commit()
                await asyncio.to_thread(kb.refresh_keyword_index)
                return {"url": normalized, "title": "", "status": "removed" if http_status in (404, 410) else "no content"}
            status = await asyncio.to_thread(kb.sync_source, page.url, page.title, page.text, page.kind, page.url)
            await _record_page(db, page.url, page.title, page.kind, changed=status != "unchanged")
            await db.commit()
        if status != "unchanged":
            await asyncio.to_thread(kb.refresh_keyword_index)
        logger.info(f"Single-page sync {normalized}: {status}")
        return {"url": page.url, "title": page.title, "status": status}


async def _record_page(db, url: str, title: str, kind: str, changed: bool):
    now = datetime.now(timezone.utc)
    page = (await db.execute(select(CrawledPage).where(CrawledPage.url == url))).scalar_one_or_none()
    if page is None:
        db.add(CrawledPage(url=url, title=title, kind=kind, status="ok", last_crawled=now, last_changed=now))
        return
    page.title, page.kind, page.last_crawled = title, kind, now
    if changed or page.status != "ok":
        page.last_changed = now
    page.status = "ok"


async def mark_interrupted_runs():
    """A run still marked 'running' at startup was cut off by a restart."""
    async with async_session() as db:
        await db.execute(
            update(CrawlRun).where(CrawlRun.status == "running")
            .values(status="failed", error="Interrupted (the backend was restarted)", finished_at=datetime.now(timezone.utc))
        )
        await db.commit()


async def _last_success() -> Optional[datetime]:
    async with async_session() as db:
        return (await db.execute(
            select(CrawlRun.finished_at).where(CrawlRun.status == "success")
            .order_by(desc(CrawlRun.finished_at)).limit(1)
        )).scalar_one_or_none()


async def schedule_loop():
    """Background task started at app startup: sync whenever the last success is older than the interval."""
    if settings.crawl_interval_hours <= 0:
        logger.info("Automatic website sync is off (CRAWL_INTERVAL_HOURS=0)")
        return
    await asyncio.sleep(15)  # let the app finish starting
    interval = timedelta(hours=settings.crawl_interval_hours)
    while True:
        try:
            last = await _last_success()
            if (last is None or datetime.now(timezone.utc) - last >= interval) and not is_running():
                await run_sync("schedule")
        except SyncAlreadyRunning:
            pass
        except Exception:
            logger.exception("Scheduled website sync failed")
        await asyncio.sleep(600)  # check again in 10 minutes
