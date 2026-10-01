from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from ..database import Base


class CrawledPage(Base):
    """One page or PDF from apsit.edu.in that is (or was) in the knowledge base."""
    __tablename__ = "crawled_pages"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False, default="")
    kind = Column(String, nullable=False, default="web")      # "web" or "pdf"
    status = Column(String, nullable=False, default="ok")     # "ok" or "removed"
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_crawled = Column(DateTime(timezone=True), nullable=False)
    last_changed = Column(DateTime(timezone=True), nullable=False)           # when its content last changed


class CrawlRun(Base):
    """One website sync (scheduled or started by an admin)."""
    __tablename__ = "crawl_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="running")  # running / success / failed
    triggered_by = Column(String, nullable=False)               # "schedule" or "admin:<email>"
    pages_seen = Column(Integer, nullable=False, default=0)
    pages_added = Column(Integer, nullable=False, default=0)
    pages_updated = Column(Integer, nullable=False, default=0)
    pages_unchanged = Column(Integer, nullable=False, default=0)
    pages_removed = Column(Integer, nullable=False, default=0)
    pages_failed = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
