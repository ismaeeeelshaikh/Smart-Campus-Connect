"""Crawler: URL rules, email decoding, PDF choice, extraction from a real saved page, safe downloads."""
from pathlib import Path

import httpx
import pytest

from app.services import crawler
from app.services.crawler import _decode_cf_email, extract_html, normalize_url, pick_pdfs

BASE = "https://www.apsit.edu.in/x"
FIXTURE = Path(__file__).parent / "fixtures" / "civil-faculty.html"


@pytest.mark.parametrize("href, expected", [
    ("/civil-faculty", "https://www.apsit.edu.in/civil-faculty"),
    ("https://apsit.edu.in/index.php/civil-engg/#top", "https://www.apsit.edu.in/civil-engg"),
    ("/news?page=2&utm=x", "https://www.apsit.edu.in/news?page=2"),
    ("/sites/default/files/2026-05/Fee%20Structure.pdf", "https://www.apsit.edu.in/sites/default/files/2026-05/Fee%20Structure.pdf"),
    ("https://google.com/", None),
    ("/sites/default/files/a.jpg", None),
    ("mailto:a@b.c", None),
    ("/user/login", None),
    ("/cdn-cgi/l/email-protection#ab", None),
])
def test_normalize_url(href, expected):
    assert normalize_url(href, BASE) == expected


def test_cloudflare_email_decoding():
    assert _decode_cf_email("294c5148446948595a405d074c4d5c074047") == "exam@apsit.edu.in"


def test_pick_pdfs_newest_first_and_no_student_lists():
    pdfs = [f"https://www.apsit.edu.in/sites/default/files/{d}/{n}.pdf" for d, n in
            [("2019-01", "old_notice"), ("2026-05", "Final_Merit_List"), ("2026-06", "Fee_Structure"), ("2025-01", "Newsletter")]]
    assert [p.rsplit("/", 1)[1] for p in pick_pdfs(pdfs, 2)] == ["Fee_Structure.pdf", "Newsletter.pdf"]


def test_extract_real_faculty_page():
    title, text, links, contact = extract_html(FIXTURE.read_text(encoding="utf-8"), "https://www.apsit.edu.in/civil-faculty")
    assert title == "Civil Faculty"
    assert ("Dr. Mugdha Agarwadkar | department: Civil Engineering | designation: Head of Department (HOD) | "
            "qualification: PhD | experience: 17 years") in text
    assert "Main navigation" not in text and "Convocation Ceremony" not in text  # menu and carousel stripped
    assert "exam@apsit.edu.in" in contact  # footer emails decoded
    assert "https://www.apsit.edu.in/dr-mugdha-agarwadkar" in links


def _site(request: httpx.Request) -> httpx.Response:
    """A fake website for download tests."""
    if request.url.host != "www.apsit.edu.in":
        return httpx.Response(200, text="<html>OTHER SITE</html>", headers={"content-type": "text/html"})
    if request.url.path == "/moved":
        return httpx.Response(301, headers={"location": "/new-home"})
    if request.url.path == "/to-evil":
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})
    if request.url.path == "/big.pdf":
        return httpx.Response(200, content=b"%PDF" + b"x" * 5000, headers={"content-type": "application/pdf"})
    return httpx.Response(200, text="<html><title>New | APSIT</title><div class='region-content'>Hello page</div></html>",
                          headers={"content-type": "text/html"})


async def test_redirects_only_within_the_college_site():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_site), follow_redirects=False) as client:
        ok = await crawler._download(client, "https://www.apsit.edu.in/moved", 10**6)
        evil = await crawler._download(client, "https://www.apsit.edu.in/to-evil", 10**6)
    assert ok.status_code == 200 and b"Hello page" in ok.content
    assert evil.off_site and evil.content == b""


async def test_downloads_have_a_size_limit():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_site), follow_redirects=False) as client:
        big = await crawler._download(client, "https://www.apsit.edu.in/big.pdf", max_bytes=1000)
    assert big.too_large and big.content == b""
