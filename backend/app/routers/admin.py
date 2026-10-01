import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..dependencies import get_admin_user
from ..models.website import CrawledPage, CrawlRun
from ..services import website_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class SinglePageRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


def _run_dict(run: CrawlRun | None):
    if run is None:
        return None
    return {
        "id": run.id, "status": run.status, "triggered_by": run.triggered_by,
        "started_at": run.started_at, "finished_at": run.finished_at,
        "pages_seen": run.pages_seen, "pages_added": run.pages_added, "pages_updated": run.pages_updated,
        "pages_unchanged": run.pages_unchanged, "pages_removed": run.pages_removed,
        "pages_failed": run.pages_failed, "error": run.error,
    }


@router.post("/website-sync")
async def start_website_sync(admin=Depends(get_admin_user)):
    """Crawl apsit.edu.in now and update the chatbot's knowledge (runs in the background)."""
    try:
        website_sync.start_in_background(f"admin:{admin.email}")
    except website_sync.SyncAlreadyRunning:
        raise HTTPException(status_code=409, detail="A website sync is already running.")
    return {"message": "Website sync started."}


@router.post("/website-sync/page")
async def sync_one_page(payload: SinglePageRequest, admin=Depends(get_admin_user)):
    """Re-read a single page right now (takes seconds), e.g. right after it was edited."""
    try:
        return await website_sync.sync_single_page(payload.url.strip())
    except website_sync.InvalidPageUrl as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception(f"Single-page sync failed for {payload.url}")
        raise HTTPException(status_code=502, detail="Could not update that page right now. Please try again.")


@router.get("/website-sync")
async def website_sync_status(admin=Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    """Current/last sync and the pages that changed most recently."""
    latest = (await db.execute(select(CrawlRun).order_by(desc(CrawlRun.id)).limit(1))).scalar_one_or_none()
    last_finished = (await db.execute(
        select(CrawlRun).where(CrawlRun.finished_at.is_not(None)).order_by(desc(CrawlRun.id)).limit(1)
    )).scalar_one_or_none()
    recent = (await db.execute(
        select(CrawledPage).order_by(desc(CrawledPage.last_changed)).limit(10)
    )).scalars().all()
    indexed = (await db.execute(select(func.count()).select_from(CrawledPage).where(CrawledPage.status == "ok"))).scalar_one()
    return {
        "running": website_sync.is_running(),
        "current": _run_dict(latest) if latest and latest.status == "running" else None,
        "last": _run_dict(last_finished),
        "pages_indexed": indexed,
        "recently_changed": [
            {"url": p.url, "title": p.title, "status": p.status, "last_changed": p.last_changed} for p in recent
        ],
    }
