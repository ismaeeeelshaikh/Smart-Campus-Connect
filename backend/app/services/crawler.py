"""Crawler for https://www.apsit.edu.in (Drupal 10).

Facts this is built on (checked 2026-09/10):
- Plain scripts get "406 Not Acceptable" from ModSecurity/Cloudflare; normal browser headers work.
- There is no sitemap, so pages are found by following links (the main menu links to most of the site).
- Each page's real content is in `.region-content`; the header, menu, carousel, sidebars and footer
  repeat on every page. Contact details from the footer are indexed once, as their own document.
- Faculty lists are grids of `article[data-history-node-id]` cards with `field--name-field-*` fields.
- Emails are hidden by Cloudflare (`/cdn-cgi/l/email-protection#<hex>`), and are decoded here.
"""
import asyncio
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from io import BytesIO
from typing import AsyncIterator, Optional
from urllib.parse import parse_qs, unquote, urldefrag, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

logger = logging.getLogger(__name__)

HOST = "www.apsit.edu.in"
BASE_URL = f"https://{HOST}"
CONTACT_SOURCE = f"{BASE_URL}/#contact"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tif", ".tiff",
    ".mp4", ".mp3", ".avi", ".mov", ".wmv", ".zip", ".rar", ".7z", ".gz",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".css", ".js", ".xml", ".json", ".txt",
)
SKIP_PATH_PREFIXES = (
    "/user", "/admin", "/search", "/node/add", "/core/", "/modules/", "/themes/", "/profiles/",
    "/cdn-cgi/", "/filter/", "/comment/", "/contact", "/rss.xml", "/batch",
)
# Lines that are page furniture, not content
JUNK_LINES = {"read more", "more", "skip to main content", "search", "next", "previous", "»", "«", "›", "‹"}
MIN_PAGE_CHARS = 30
# PDFs whose content is NOT indexed because they list individual students (names, marks, ranks).
# The page linking to them still mentions them, with the link.
PERSONAL_DATA_PDF_RE = re.compile(r"merit|rank|selected|allot|enrolled|student.?list|list.?of.?(students|candidates)", re.I)
PDF_DATE_RE = re.compile(r"/files/(\d{4}-\d{2})/")


@dataclass
class Page:
    url: str
    title: str
    text: str
    kind: str  # "web" (HTML page) or "pdf"


@dataclass
class CrawlResult:
    pages_ok: int = 0
    pdfs_ok: int = 0
    not_found: list[str] = field(default_factory=list)  # 404/410: page was deleted
    failed: list[str] = field(default_factory=list)      # network errors, 5xx, unreadable
    skipped_duplicates: int = 0
    hit_page_limit: bool = False
    pdf_links: set[str] = field(default_factory=set)       # every PDF linked from a crawled page


def normalize_url(href: str, base: str) -> Optional[str]:
    """Absolute, canonical https://www.apsit.edu.in URL, or None if it's not a crawlable page/PDF."""
    href = (href or "").strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    url, _ = urldefrag(urljoin(base, href))
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return None
    host = p.netloc.lower().split(":")[0]
    if host == "apsit.edu.in":
        host = HOST
    if host != HOST:
        return None
    path = re.sub(r"^/index\.php(?=/|$)", "", p.path) or "/"
    path = re.sub(r"/{2,}", "/", path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    lower = path.lower()
    if lower.startswith(SKIP_PATH_PREFIXES) or lower.endswith(SKIP_EXTENSIONS):
        return None
    if lower.startswith("/sites/") and not lower.endswith(".pdf"):
        return None  # images and other uploaded files
    page = parse_qs(p.query).get("page")  # keep only Drupal's pager parameter
    return urlunparse(("https", host, path, "", f"page={page[0]}" if page else "", ""))


def _decode_cf_email(hex_string: str) -> str:
    key = int(hex_string[:2], 16)
    return "".join(chr(int(hex_string[i:i + 2], 16) ^ key) for i in range(2, len(hex_string), 2))


def _decode_emails(soup: BeautifulSoup):
    for tag in soup.select("[data-cfemail]"):
        try:
            tag.replace_with(_decode_cf_email(tag["data-cfemail"]))
        except (ValueError, KeyError):
            pass
    for a in soup.select('a[href*="/cdn-cgi/l/email-protection#"]'):
        try:
            a.replace_with(_decode_cf_email(a["href"].split("#", 1)[1]))
        except (ValueError, IndexError):
            pass


def _clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and line.lower() not in JUNK_LINES:
            lines.append(line)
    # drop immediate repeats (e.g. a link text followed by the same caption)
    deduped = [line for i, line in enumerate(lines) if i == 0 or line != lines[i - 1]]
    return "\n".join(deduped)


def _card_sentence(card, page_url: str) -> Optional[str]:
    """Turn a listing card (e.g. a faculty card) into one line with all its fields."""
    heading = card.find(["h2", "h3"])
    name = heading.get_text(" ", strip=True) if heading else ""
    parts = []
    for f in card.select("[class*='field--name-field-']"):
        cls = next((c for c in f.get("class", []) if c.startswith("field--name-field-")), "")
        label = cls.removeprefix("field--name-field-")
        if label in ("image", "photo", "picture"):
            continue
        items = [i.get_text(" ", strip=True) for i in f.select(".field__item")] or [f.get_text(" ", strip=True)]
        value = ", ".join(v for v in items if v)
        if value:
            label = "experience" if label == "year-of-passing" else label.replace("-", " ")
            if "head of department" in value.lower() and "hod" not in value.lower():
                value += " (HOD)"  # people search for "HOD"; the site only writes it out in full
            parts.append(f"{label}: {value}")
    if not name or not parts:
        return None
    link = heading.find("a", href=True) if heading else None
    profile = normalize_url(link["href"], page_url) if link else None
    return f"{name} | " + " | ".join(parts) + (f" | profile: {profile}" if profile else "")


def extract_html(html: str, url: str) -> tuple[str, str, list[str], str]:
    """-> (title, content text, links found on the page, footer contact text)."""
    soup = BeautifulSoup(html, "lxml")
    _decode_emails(soup)

    links = []
    for a in soup.find_all("a", href=True):
        normalized = normalize_url(a["href"], url)
        if normalized:
            links.append(normalized)

    title = soup.title.get_text(" ", strip=True) if soup.title else url
    title = re.sub(r"\s*\|\s*APSIT\s*$", "", title) or url

    contact = " ".join(r.get_text(" ", strip=True) for r in soup.select("[class*='region-panel-second']"))

    content = soup.select_one(".region-content") or soup.find("main") or soup.body or soup
    for tag in content.select("script, style, noscript, iframe, form, nav, .visually-hidden, .pager, .contextual"):
        tag.decompose()
    # Keep PDF links in the text, so the chatbot can point to documents it hasn't read
    for a in content.select('a[href$=".pdf"], a[href$=".PDF"]'):
        pdf_url = normalize_url(a["href"], url)
        if pdf_url:
            a.append(f" (PDF: {pdf_url})")
    # Listing cards (faculty grids, news teasers) -> one line each
    for card in content.select(".view-content article, .views-row article"):
        sentence = _card_sentence(card, url)
        if sentence:
            card.replace_with(soup.new_string(f"\n{sentence}\n"))

    return title, _clean_text(content.get_text("\n")), links, contact


def extract_pdf(data: bytes, max_pages: int, max_chars: int = 40_000) -> str:
    reader = PdfReader(BytesIO(data))
    texts = []
    for page in reader.pages[:max_pages]:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return _clean_text("\n".join(texts))[:max_chars]


def pdf_title(url: str) -> str:
    name = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    return re.sub(r"\.pdf$", "", name, flags=re.I).replace("_", " ") + " (PDF)"


def pick_pdfs(pdf_links: list[str], max_pdfs: int) -> list[str]:
    """Newest uploads first (Drupal stores files under /files/YYYY-MM/), skipping student lists."""
    allowed = [u for u in pdf_links if not PERSONAL_DATA_PDF_RE.search(unquote(u.rsplit("/", 1)[-1]))]
    allowed.sort(key=lambda u: (m.group(1) if (m := PDF_DATE_RE.search(u)) else "0000-00"), reverse=True)
    return allowed[:max_pdfs]


@dataclass
class Fetched:
    status_code: int
    content_type: str
    content: bytes = b""
    encoding: Optional[str] = None
    too_large: bool = False
    off_site: bool = False  # redirected away from www.apsit.edu.in

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding or "utf-8", errors="replace")


async def _page_from_response(response: Fetched, url: str, max_pdf_mb: float, max_pdf_pages: int):
    """-> (Page or None, links, contact text). None when the response has no usable content."""
    if response.too_large or response.off_site:
        return None, [], ""
    content_type = response.content_type
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        text = await asyncio.to_thread(extract_pdf, response.content, max_pdf_pages)
        if len(text) < 200:  # scanned PDF (image only) - would need OCR
            return None, [], ""
        return Page(url, pdf_title(url), text, "pdf"), [], ""
    if "text/html" not in content_type:
        return None, [], ""
    title, text, links, contact = extract_html(response.text, url)
    if len(text) < MIN_PAGE_CHARS:
        return None, links, contact
    return Page(url, title, text, "web"), links, contact


async def fetch_single(url: str, max_pdf_mb: float = 8, max_pdf_pages: int = 25) -> tuple[Optional[int], Optional[Page]]:
    """Fetch one page or PDF -> (HTTP status or None if unreachable, Page or None if no usable content)."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=False) as client:
        response = await _fetch(client, url, int(max_pdf_mb * 1024 * 1024))
    if response is None:
        return None, None
    if response.status_code >= 400:
        return response.status_code, None
    page, _, _ = await _page_from_response(response, url, max_pdf_mb, max_pdf_pages)
    return response.status_code, page


DOWNLOAD_DEADLINE_SECONDS = 90


MAX_REDIRECTS = 5


async def _download(client: httpx.AsyncClient, url: str, max_bytes: int) -> Fetched:
    # Redirects are followed by hand, and only within www.apsit.edu.in: we never request or
    # index another site (or an internal address) because a page redirected there.
    for _ in range(MAX_REDIRECTS + 1):
        async with client.stream("GET", url) as r:
            content_type = r.headers.get("content-type", "")
            if r.is_redirect:
                target = normalize_url(r.headers.get("location", ""), url)
                if target is None:
                    return Fetched(r.status_code, content_type, off_site=True)
                url = target
                continue
            if r.status_code >= 400:
                return Fetched(r.status_code, content_type)
            if int(r.headers.get("content-length") or 0) > max_bytes:
                return Fetched(r.status_code, content_type, too_large=True)  # don't download it at all
            body = bytearray()
            async for chunk in r.aiter_bytes():
                body += chunk
                if len(body) > max_bytes:
                    return Fetched(r.status_code, content_type, too_large=True)
            return Fetched(r.status_code, content_type, bytes(body), r.encoding)
    return Fetched(310, "", off_site=True)  # too many redirects


async def _fetch(client: httpx.AsyncClient, url: str, max_bytes: int) -> Optional[Fetched]:
    """GET with a size cap and an overall time limit, retrying network errors and 5xx.
    Returns None if every attempt failed."""
    for attempt in range(3):
        try:
            response = await asyncio.wait_for(_download(client, url, max_bytes), DOWNLOAD_DEADLINE_SECONDS)
            if response.status_code < 500:
                return response
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            logger.debug(f"Fetch error {url}: {e!r}")
        await asyncio.sleep(2 ** attempt)
    return None


async def crawl(
    max_pages: int = 400,
    delay: float = 0.5,
    include_pdfs: bool = True,
    max_pdfs: int = 60,
    max_pdf_mb: float = 8,
    max_pdf_pages: int = 25,
    result: Optional[CrawlResult] = None,
) -> AsyncIterator[Page]:
    """Yield every page of the site (breadth-first from the home page), then linked PDFs.
    Pass a CrawlResult to collect statistics."""
    result = result if result is not None else CrawlResult()
    max_bytes = int(max_pdf_mb * 1024 * 1024)
    queue, queued = deque([BASE_URL + "/"]), {BASE_URL + "/"}
    pdf_links: dict[str, None] = {}  # ordered set
    seen_content: set[int] = set()
    contact_done = False

    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=False) as client:
        while queue:
            if result.pages_ok >= max_pages:
                result.hit_page_limit = True
                break
            url = queue.popleft()
            await asyncio.sleep(delay)
            response = await _fetch(client, url, max_bytes)
            if response is None or response.status_code >= 400:
                (result.not_found if response is not None and response.status_code in (404, 410) else result.failed).append(url)
                continue
            try:
                page, links, contact = await _page_from_response(response, url, max_pdf_mb, max_pdf_pages)
            except Exception:
                logger.exception(f"Could not read {url}")
                result.failed.append(url)
                continue
            for link in links:
                if link.lower().endswith(".pdf"):
                    pdf_links.setdefault(link)
                elif link not in queued:
                    queued.add(link)
                    queue.append(link)

            if contact and not contact_done:
                contact_done = True
                yield Page(CONTACT_SOURCE, "APSIT contact information", contact, "web")

            if page is None or page.kind != "web":
                continue
            # The same page is often reachable under two URLs (/node/123 and its alias)
            fingerprint = hash(page.text)
            if fingerprint in seen_content:
                result.skipped_duplicates += 1
                continue
            seen_content.add(fingerprint)
            result.pages_ok += 1
            yield page

        result.pdf_links = set(pdf_links)
        if not include_pdfs:
            return
        for url in pick_pdfs(list(pdf_links), max_pdfs):
            await asyncio.sleep(delay)
            response = await _fetch(client, url, max_bytes)
            if response is None or response.status_code >= 400:
                (result.not_found if response is not None and response.status_code in (404, 410) else result.failed).append(url)
                continue
            try:
                page, _, _ = await _page_from_response(response, url, max_pdf_mb, max_pdf_pages)
            except Exception:
                result.failed.append(url)
                continue
            if page is not None:
                result.pdfs_ok += 1
                yield page
