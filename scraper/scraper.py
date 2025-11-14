"""Playwright-based scraper with Requests+BeautifulSoup fallback.

Provides a simple function `scrape_table` that extracts rows from an HTML table
or selector and returns a list of dicts (rows).

The Playwright import is done lazily so the module can be imported even if
Playwright isn't installed; code will fall back to requests/bs4.
"""
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


def _parse_table_html(html: str, row_selector: str, header_selector: Optional[str] = None) -> List[Dict]:
    """Parse HTML and extract rows using selectors.

    Args:
        html: HTML content
        row_selector: CSS selector that matches row elements (e.g., 'table tr')
        header_selector: Optional selector for header cells (e.g., 'table thead tr th')

    Returns:
        List of dicts representing rows. Keys are header names if available else numbered columns.
    """
    soup = BeautifulSoup(html, "lxml")

    # Try to build headers
    headers = []
    if header_selector:
        header_cells = soup.select(header_selector)
        if header_cells:
            # If header_selector matches a row, take its th/td children
            ths = []
            for h in header_cells:
                for cell in h.find_all(["th", "td"]):
                    ths.append(cell.get_text(strip=True))
            if ths:
                headers = ths

    rows = []
    for r in soup.select(row_selector):
        cells = [c.get_text(strip=True) for c in r.find_all(["td", "th"])]
        if not cells:
            continue
        if not headers:
            # create numeric headers
            headers = [f"col_{i}" for i in range(1, len(cells) + 1)]
        # ensure length
        row = {headers[i] if i < len(headers) else f"col_{i+1}": cells[i] for i in range(len(cells))}
        rows.append(row)
    return rows


def scrape_with_requests(url: str, row_selector: str, header_selector: Optional[str] = None, timeout: int = 30) -> List[Dict]:
    """Fetch page with requests and parse table rows."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return _parse_table_html(resp.text, row_selector, header_selector)


def scrape_with_playwright(url: str, row_selector: str, header_selector: Optional[str] = None, timeout: int = 30) -> List[Dict]:
    """Use Playwright to render the page and extract table rows.

    Raises ImportError if Playwright isn't installed.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise ImportError("Playwright not available: %s" % e)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout * 1000)
        # Wait a little for dynamic content
        page.wait_for_timeout(500)
        html = page.content()
        browser.close()
    return _parse_table_html(html, row_selector, header_selector)


def scrape(url: str, row_selector: str, header_selector: Optional[str] = None, prefer_playwright: bool = True) -> List[Dict]:
    """High-level scraper: try Playwright first (if preferred), else fallback to requests.

    Returns list of row dicts.
    """
    if prefer_playwright:
        try:
            return scrape_with_playwright(url, row_selector, header_selector)
        except Exception:
            # fallback silently to requests
            return scrape_with_requests(url, row_selector, header_selector)
    else:
        return scrape_with_requests(url, row_selector, header_selector)
