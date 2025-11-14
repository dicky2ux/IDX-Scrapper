"""Client for IDX announcements API and keyword filtering utilities.

This module provides:
- `filter_reply(reply, keywords)` to test whether a single announcement reply
  matches any of the provided keywords (case-insensitive substring match across
  relevant fields).
- `fetch_matching_announcements(...)` to paginate the IDX API and yield matching
  replies. (Uses requests; does not require Playwright.)

"""

from typing import Dict, Iterable, Optional, List
import requests
from datetime import datetime, timedelta


def _fetch_page_with_playwright(params: Dict) -> Dict:
    """Fetch the API endpoint using Playwright to avoid server-side blocking.

    Returns the parsed JSON dict. Raises ImportError if Playwright not installed
    or other exceptions from Playwright if fetching fails.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise ImportError("Playwright not available: %s" % e)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        # First visit main site to allow any anti-bot JS to run
        try:
            page.goto("https://www.idx.co.id/", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            # ignore warm-up errors
            pass

        from urllib.parse import urlencode

        url = IDX_API_URL + "?" + urlencode(params)
        # fetch text from API endpoint in page context
        text = page.evaluate(
            "(url) => fetch(url, {headers: {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest','Referer':'https://www.idx.co.id/'} }).then(r=>r.text())",
            url,
        )
        browser.close()

        import json

        try:
            return json.loads(text)
        except Exception as e:
            excerpt = (text or "")[:500]
            raise RuntimeError(
                f"Playwright fetched non-JSON response: {e}; excerpt: {excerpt}"
            )


def session_from_playwright_interactive() -> "requests.Session":
    """Open Playwright in headed mode and let user complete any challenges.

    After user confirms (press Enter in terminal), capture cookies from the
    browser context and return a requests.Session populated with those cookies.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise ImportError("Playwright not available: %s" % e)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.idx.co.id/")
        print(
            "Playwright opened a browser window. Please solve any challenge on the page, then return here and press Enter to continue..."
        )
        input("Press Enter after you've completed any challenge in the browser...")
        # capture cookies
        cookies = context.cookies()
        browser.close()

    session = requests.Session()
    for c in cookies:
        session.cookies.set(
            c.get("name"), c.get("value"), domain=c.get("domain"), path=c.get("path")
        )
    return session


# Base endpoint
IDX_API_URL = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"

# Default keywords list (from user's request). Kept as original phrases; normalization
# will lowercase and normalize smart quotes for matching.
DEFAULT_KEYWORDS = [
    "Prospektus",
    "Pengambilalihan",
    "Negosiasi Pengambilalihan",
    "Penawaran Tender Wajib",
    "Penawaran Tender",
    "Mandatory Tender Offer",
    "MTO",
    "Transaksi Material",
    "Transaksi Afiliasi",
    "Perubahan Kegiatan Usaha",
    "Perjanjian Pengikatan Jual Beli",
    "Perjanjian Jual Beli",
    "PPJB",
    "Hak Memesan Efek",
    "HMETD",
    "CSPA",
    "Kontrak Penting",
]


def _normalize_keyword(k: str) -> str:
    # normalize smart quotes and surrounding whitespace
    k = k.replace("“", '"').replace("”", '"')
    return k.strip().lower()


def filter_reply(reply: Dict, keywords: Iterable[str]) -> bool:
    """Return True if any of the keywords is found in the reply's text fields.

    We search common text fields: JudulPengumuman, PerihalPengumuman,
    NoPengumuman, Kode_Emiten and attachment OriginalFilename(s).
    Matching is case-insensitive substring match.
    """
    if not reply:
        return False

    import re

    # normalize keywords to lowercase and replace non-alphanum with spaces so
    # that filenames like 'dokumen_Penawaran_Tender.pdf' match 'Penawaran Tender'
    normalized_keywords = [
        re.sub(r"[^0-9a-z]+", " ", _normalize_keyword(k)) for k in keywords if k
    ]
    if not normalized_keywords:
        return False

    # collect candidate text fields
    peng = reply.get("pengumuman") or {}
    candidates = []
    for key in ("JudulPengumuman", "PerihalPengumuman", "NoPengumuman", "Kode_Emiten"):
        v = peng.get(key)
        if v:
            candidates.append(str(v))

    # attachments' original filenames
    for att in reply.get("attachments") or []:
        orig = att.get("OriginalFilename") or att.get("PDFFilename")
        if orig:
            candidates.append(str(orig))

    hay = "\n".join(candidates).lower()
    # normalize hay similarly (replace punctuation/underscores with spaces)
    hay_norm = re.sub(r"[^0-9a-z]+", " ", hay)

    for k in normalized_keywords:
        if k and k in hay_norm:
            return True
    return False


def fetch_matching_announcements(
    keywords: Iterable[str],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    emiten_type: str = "*",
    lang: str = "id",
    page_size: int = 100,
    max_pages: Optional[int] = None,
) -> Iterable[Dict]:
    """Paginate the IDX API and yield replies that match keywords.

    Note: This function performs live HTTP requests. Use responsibly and obey
    the target site's terms of use. `max_pages` can be set to limit how many
    pages are fetched (useful for testing).
    """
    # compute sensible defaults if not provided: date_to = today, date_from = 2 days ago
    if date_to is None:
        today = datetime.now().date()
        # use YYYYMMDD format as requested
        date_to = today.strftime("%Y%m%d")
    if date_from is None:
        two_days = datetime.now().date() - timedelta(days=2)
        # use YYYYMMDD format as requested
        date_from = two_days.strftime("%Y%m%d")

    params = {
        "emitenType": emiten_type,
        "dateFrom": date_from,
        "dateTo": date_to,
        "lang": lang,
        "keyword": "",
        # indexFrom and pageSize set per request
    }

    index_from = 0
    pages_fetched = 0
    while True:
        # requests params should be strings
        params.update({"indexFrom": str(index_from), "pageSize": str(page_size)})
        # Use a session and perform an initial GET to the main site to obtain cookies
        # and any anti-bot tokens. Add common AJAX headers as well.
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.idx.co.id/",
            "Origin": "https://www.idx.co.id",
            "X-Requested-With": "XMLHttpRequest",
        }

        # Warm up session (get cookies)
        try:
            session.get("https://www.idx.co.id/", headers=headers, timeout=10)
        except Exception:
            # ignore warm-up errors; we'll still try the API call
            pass

        r = session.get(IDX_API_URL, params=params, headers=headers, timeout=30)
        data = None
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            # If server returns 403, try a second time with a slightly different UA
            if r.status_code == 403:
                alt_headers = headers.copy()
                alt_headers["User-Agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                try:
                    r2 = session.get(
                        IDX_API_URL, params=params, headers=alt_headers, timeout=30
                    )
                    r2.raise_for_status()
                    r = r2
                except requests.exceptions.HTTPError:
                    # Both requests attempts got 403 — try Playwright fallback
                    try:
                        data = _fetch_page_with_playwright(params)
                    except Exception:
                        # re-raise original 403 if Playwright also fails
                        raise
            else:
                raise
        if data is None:
            data = r.json()

        replies = data.get("Replies") or []
        for rep in replies:
            if filter_reply(rep, keywords):
                yield rep

        # paging logic
        total = data.get("ResultCount")
        index_from += page_size
        pages_fetched += 1
        if max_pages is not None and pages_fetched >= max_pages:
            break
        # stop when we've fetched all
        if total is None:
            break
        if index_from >= int(total):
            break


def fetch_replies_for_keyword(
    keyword: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    emiten_type: str = "*",
    lang: str = "id",
    page_size: int = 10000,
    session: Optional[requests.Session] = None,
) -> List[Dict]:
    """Fetch raw Replies list from IDX API for a single keyword.

    Tries requests then Playwright fallback on 403. Returns list of reply dicts
    (may be empty).
    """
    # compute sensible defaults if not provided: date_to = today, date_from = 2 days ago
    if date_to is None:
        today = datetime.now().date()
        # use YYYYMMDD format as requested
        date_to = today.strftime("%Y%m%d")
    if date_from is None:
        two_days = datetime.now().date() - timedelta(days=2)
        # use YYYYMMDD format as requested
        date_from = two_days.strftime("%Y%m%d")

    params = {
        "emitenType": emiten_type,
        "dateFrom": date_from,
        "dateTo": date_to,
        "lang": lang,
        "keyword": keyword,
        "indexFrom": "0",
        "pageSize": str(page_size),
    }

    # allow passing an already-warmed requests.Session (e.g. from
    # session_from_playwright_interactive) so the caller can reuse cookies
    # obtained interactively. If none provided, create a new session.
    if session is None:
        session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.idx.co.id/",
        "Origin": "https://www.idx.co.id",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        session.get("https://www.idx.co.id/", headers=headers, timeout=10)
    except Exception:
        pass

    r = session.get(IDX_API_URL, params=params, headers=headers, timeout=30)
    try:
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.HTTPError:
        # try alt UA
        if r.status_code == 403:
            alt = headers.copy()
            alt["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            try:
                r2 = session.get(IDX_API_URL, params=params, headers=alt, timeout=30)
                print(f"Fetching URL: {r2.url}")
                r2.raise_for_status()
                data = r2.json()
            except requests.exceptions.HTTPError:
                # Playwright fallback
                data = _fetch_page_with_playwright(params)
        else:
            raise

    return data.get("Replies") or []
