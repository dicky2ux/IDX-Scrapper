"""Export Kode_Emiten, Judul_Pengumuman, and Tanggal_Pengumuman for DEFAULT_KEYWORDS.

This is a minimal, robust exporter:
- uses the scraper.idx_api helpers for non-browser requests
- falls back to an interactive Playwright browser fetch when --interactive is given
- deduplicates and sorts results by date (newest first)
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests
import os

# Optionally load a .env file if python-dotenv is installed. This keeps the feature
# optional: the script will still work if python-dotenv isn't available and the
# user provides env vars by other means (shell, CI secrets).
try:
    from dotenv import load_dotenv  # type: ignore

    # load .env from project root / current working dir (no override of existing env vars)
    load_dotenv(override=False)
except Exception:
    # python-dotenv not installed or .env not present — that's fine.
    pass

from scraper.idx_api import DEFAULT_KEYWORDS, fetch_replies_for_keyword

# Optional keyring support for secure credential storage
try:
    import keyring  # type: ignore
except Exception:
    keyring = None

import sys
import subprocess


# Default paths for Playwright storage state and exported cookies
# Use XDG_CONFIG_HOME or ~/.config/idx-scraper for persistent storage (cron/CI friendly)
_config_base = (
    Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "idx-scraper"
)
_config_base.mkdir(parents=True, exist_ok=True)
DEFAULT_STORAGE_STATE = _config_base / "playwright_storage_state.json"
DEFAULT_COOKIE_EXPORT = _config_base / "session_cookies.json"


def storage_state_has_auth(path: Path) -> bool:
    """Return True if the Playwright storage state at `path` contains an auth token in
    localStorage or a cookie named 'auth._token.local'."""
    if not path or not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    try:
        # check cookies
        for c in data.get("cookies", []) or []:
            if c.get("name") == "auth._token.local":
                return True
        # check origins/localStorage
        for origin in data.get("origins", []) or []:
            for kv in origin.get("localStorage", []) or []:
                if kv.get("name") == "auth._token.local":
                    return True
    except Exception:
        return False
    return False


def perform_interactive_login_and_save(
    email: str,
    password: str,
    storage_path: Path = DEFAULT_STORAGE_STATE,
    proxy_url: Optional[str] = None,
    headless: bool = False,
) -> bool:
    """Perform a Playwright login using provided credentials and save storage state.

    Behavior:
    - If headless=True, attempt a programmatic (non-interactive) login first.
      If that fails or Cloudflare challenge blocks the flow, fall back to a headed
      interactive session so the user can solve the challenge manually.

    Returns True on success.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("Playwright not available for login:", e)
        return False

    try:
        with sync_playwright() as pw:

            def _launch(use_headed: bool, use_proxy: Optional[str] = proxy_url):
                launch_args = {}
                if use_proxy:
                    proxy_server = (
                        use_proxy
                        if use_proxy.startswith("http")
                        else "http://" + use_proxy
                    )
                    launch_args["proxy"] = {"server": proxy_server}
                return pw.chromium.launch(headless=not use_headed, **launch_args)

            # Try programmatic (headless) login first if requested, otherwise start headed
            try_headless = headless

            def _attempt_login(use_headed: bool) -> bool:
                try:
                    browser = _launch(use_headed, proxy_url)
                except Exception as e:
                    print(
                        "Playwright launch failed with proxy; retrying without proxy. Error:",
                        e,
                    )
                    try:
                        browser = _launch(use_headed, None)
                    except Exception as e2:
                        print("Playwright launch failed without proxy:", e2)
                        return False

                context = browser.new_context(locale="id-ID")
                page = context.new_page()
                try:
                    page.goto("https://www.idx.co.id/", timeout=60000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=60000)
                    except Exception:
                        pass
                except Exception as e:
                    print("Navigation failed during login attempt:", e)
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return False

                # Try clicking common login triggers
                for sel in [
                    "text=Login",
                    "text=Masuk",
                    "a:has-text('Login')",
                    "a:has-text('Masuk')",
                ]:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            el.click()
                            break
                    except Exception:
                        continue

                page.wait_for_timeout(1500)

                # Fill common fields
                try:
                    if page.query_selector('input[type="email"]'):
                        page.fill('input[type="email"]', email)
                    elif page.query_selector('input[name="email"]'):
                        page.fill('input[name="email"]', email)
                    elif page.query_selector('input[name="username"]'):
                        page.fill('input[name="username"]', email)
                except Exception:
                    pass
                try:
                    if page.query_selector('input[type="password"]'):
                        page.fill('input[type="password"]', password)
                    elif page.query_selector('input[name="password"]'):
                        page.fill('input[name="password"]', password)
                except Exception:
                    pass

                # Submit
                for bsel in [
                    "button[type=submit]",
                    "button:has-text('Login')",
                    "button:has-text('Masuk')",
                    "text=Sign in",
                ]:
                    try:
                        el = page.query_selector(bsel)
                        if el:
                            el.click()
                            break
                    except Exception:
                        continue

                # Wait briefly for navigation/auth to settle
                page.wait_for_timeout(4000)

                # Check storage state to see if login succeeded (look for auth token)
                try:
                    ss = context.storage_state()
                    # write immediately so callers can inspect
                    storage_path.write_text(json.dumps(ss, indent=2), encoding="utf-8")
                    cookie_dump = {"cookies": ss.get("cookies", [])}
                    DEFAULT_COOKIE_EXPORT.write_text(
                        json.dumps(cookie_dump, indent=2), encoding="utf-8"
                    )
                    # detect auth token in storage
                    has_auth = False
                    for c in ss.get("cookies", []) or []:
                        if c.get("name") == "auth._token.local":
                            has_auth = True
                            break
                    for origin in ss.get("origins", []) or []:
                        for kv in origin.get("localStorage", []) or []:
                            if kv.get("name") == "auth._token.local":
                                has_auth = True
                                break
                        if has_auth:
                            break
                    if has_auth:
                        print(f"Saved Playwright storage state to {storage_path}")
                        try:
                            browser.close()
                        except Exception:
                            pass
                        return True
                except Exception as e:
                    print("Login/save check failed:", e)

                # If we reach here and we're in headed mode, allow user to solve further
                if use_headed:
                    print(
                        "If login did not complete automatically, please complete login in the opened browser window."
                    )
                    try:
                        input(
                            "Press Enter after you've completed login/challenge in the browser..."
                        )
                    except Exception:
                        pass
                    try:
                        ss = context.storage_state()
                        storage_path.write_text(
                            json.dumps(ss, indent=2), encoding="utf-8"
                        )
                        cookie_dump = {"cookies": ss.get("cookies", [])}
                        DEFAULT_COOKIE_EXPORT.write_text(
                            json.dumps(cookie_dump, indent=2), encoding="utf-8"
                        )
                        print(f"Saved Playwright storage state to {storage_path}")
                        try:
                            browser.close()
                        except Exception:
                            pass
                        return True
                    except Exception as e:
                        print("Final save failed:", e)
                        try:
                            browser.close()
                        except Exception:
                            pass
                        return False

                try:
                    browser.close()
                except Exception:
                    pass
                return False

            # Try headless/programmatic first if requested
            if try_headless:
                ok = _attempt_login(use_headed=False)
                if ok:
                    return True
                print(
                    "Headless/programmatic login failed or was blocked; will retry in headed mode."
                )

            # Fallback to headed interactive
            return _attempt_login(use_headed=True)
    except Exception as e:
        print("Login flow failed:", e)
        return False


def session_from_storage_state(path: Path) -> Optional[requests.Session]:
    """Create a requests.Session from a Playwright storageState JSON file.

    Returns None if the file does not exist or cannot be parsed.
    """
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    cookies = data.get("cookies") or []
    if not cookies:
        return None
    s = requests.Session()
    for c in cookies:
        name = c.get("name")
        val = c.get("value")
        domain = c.get("domain")
        pathv = c.get("path") or "/"
        if name and val:
            try:
                s.cookies.set(name, val, domain=domain, path=pathv)
            except Exception:
                # best-effort; ignore malformed cookie
                s.cookies.set(name, val)
    return s


def parse_date(s: str) -> datetime:
    if not s:
        return datetime.min
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    fmts = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue
    return datetime.min


def session_from_cookie_header(cookie_header: str) -> requests.Session:
    s = requests.Session()
    for part in cookie_header.split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            continue
        name, val = part.strip().split("=", 1)
        s.cookies.set(name, val, domain=".idx.co.id", path="/")
    return s


def browser_fetch_all(
    keywords: List[str],
    output_path: Path,
    debug: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    proxy_url: Optional[str] = None,
) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("Playwright not available: %s" % e)

    rows: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()

    from datetime import datetime, timedelta

    # allow caller to override date_from/date_to; otherwise default to last 2 days
    if not date_to or not date_from:
        today = datetime.now().date()
        default_to = today.strftime("%Y%m%d")
        default_from = (today - timedelta(days=7)).strftime("%Y%m%d")
        date_to = date_to or default_to
        date_from = date_from or default_from

    with sync_playwright() as pw:
        launch_args = {}
        if proxy_url:
            proxy_server = (
                proxy_url if proxy_url.startswith("http") else "http://" + proxy_url
            )
            launch_args["proxy"] = {"server": proxy_server}
        browser = pw.chromium.launch(headless=False, **launch_args)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.idx.co.id/", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)
        print("Browser opened. If a challenge appears, solve it in the opened window.")
        input("Press Enter after you've completed any challenge in the browser...")

        # After user interaction, save storage state so future non-interactive runs can reuse it
        try:
            ss = context.storage_state()
            DEFAULT_STORAGE_STATE.write_text(json.dumps(ss, indent=2), encoding="utf-8")
            print(f"Saved Playwright storage state to {DEFAULT_STORAGE_STATE}")
            # Also write a cookie-only export for requests-based reuse
            cookie_dump = {"cookies": ss.get("cookies", [])}
            DEFAULT_COOKIE_EXPORT.write_text(
                json.dumps(cookie_dump, indent=2), encoding="utf-8"
            )
            print(f"Wrote cookies to {DEFAULT_COOKIE_EXPORT}")
        except Exception as e:
            print("Failed saving storage state:", e)

        if debug and keywords:
            probe = keywords[0]
            api_url = (
                "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
                + f"?keyword={probe}&indexFrom=0&pageSize=10&dateFrom={date_from}&dateTo={date_to}"
            )
            try:
                text = page.evaluate(
                    "(u) => fetch(u, {headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest','Referer':'https://www.idx.co.id/'}}).then(r=>r.text())",
                    api_url,
                )
                print("Debug fetched (len):", len(text or ""))
                print((text or "")[:1000])
            except Exception as e:
                print("Debug fetch failed:", e)

        for kw in keywords:
            print("Browser fetching:", kw)
            api_url = (
                "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
                + f"?keyword={kw}&indexFrom=0&pageSize=100&dateFrom={date_from}&dateTo={date_to}"
            )
            try:
                text = page.evaluate(
                    "(u) => fetch(u, {headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest','Referer':'https://www.idx.co.id/'}}).then(r=>r.text())",
                    api_url,
                )
                data = json.loads(text)
            except Exception as e:
                print("  fetch error:", e)
                data = {}

            replies = data.get("Replies") or []
            for r in replies:
                peng = r.get("pengumuman") or r.get("Pengumuman") or {}
                kode = (peng.get("Kode_Emiten") or r.get("Kode_Emiten") or "").strip()
                judul = (
                    peng.get("JudulPengumuman") or peng.get("Judul_Pengumuman") or ""
                ).strip()
                tanggal = (
                    peng.get("TglPengumuman") or peng.get("Tanggal") or ""
                ).strip()
                key = (kode, judul, tanggal)
                if not kode and not judul:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "Kode_Emiten": kode,
                        "Judul_Pengumuman": judul,
                        "Tanggal_Pengumuman": tanggal,
                    }
                )

        browser.close()

    # sort by date desc
    rows.sort(key=lambda r: parse_date(r.get("Tanggal_Pengumuman") or ""), reverse=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Kode_Emiten", "Judul_Pengumuman", "Tanggal_Pengumuman"],
            delimiter=";",
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return len(rows)


def playwright_automated_fetch_all(
    keywords: List[str],
    output_path: Path,
    headless: bool = True,
    debug: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    auth_token: Optional[str] = None,
    proxy_url: Optional[str] = None,
) -> int:
    """Use Playwright to automatically fetch all keywords using the browser (no manual interaction).

    This launches a browser context (headless by default), navigates to the IDX site to allow the
    site to set required client state, then uses page.evaluate to fetch the JSON API for each
    keyword. The storage state is saved after the run.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("Playwright not available: %s" % e)

    rows: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()

    from datetime import datetime, timedelta

    # allow caller override, otherwise default to last 2 days
    if not date_to or not date_from:
        today = datetime.now().date()
        default_to = today.strftime("%Y%m%d")
        default_from = (today - timedelta(days=7)).strftime("%Y%m%d")
        date_to = date_to or default_to
        date_from = date_from or default_from

    with sync_playwright() as pw:

        def _launch_ctx(hd: bool, use_proxy: Optional[str] = proxy_url):
            launch_args = {}
            if use_proxy:
                proxy_server = (
                    use_proxy if use_proxy.startswith("http") else "http://" + use_proxy
                )
                launch_args["proxy"] = {"server": proxy_server}
            return pw.chromium.launch(headless=hd, **launch_args)

        # attempt with proxy first, fall back to no-proxy if navigation fails
        try:
            browser = _launch_ctx(headless, proxy_url)
        except Exception as e:
            print(
                "Playwright launch with proxy failed; retrying without proxy. Error:", e
            )
            try:
                browser = _launch_ctx(headless, None)
            except Exception as e2:
                raise RuntimeError(
                    "Playwright launch failed (with and without proxy): %s" % e2
                )
        # create context with typical locale/UA to mimic real browser
        # If we have a saved storage state, load it so non-interactive runs can reuse cookies/localStorage
        storage_state_obj = None
        try:
            if DEFAULT_STORAGE_STATE.exists():
                storage_state_obj = json.loads(
                    DEFAULT_STORAGE_STATE.read_text(encoding="utf-8")
                )
        except Exception:
            storage_state_obj = None

        if storage_state_obj:
            context = browser.new_context(
                locale="id-ID",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36",
                storage_state=storage_state_obj,
            )
        else:
            context = browser.new_context(
                locale="id-ID",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36",
            )
        page = context.new_page()
        # Navigate to homepage to let Cloudflare/IDX set any required cookies
        try:
            page.goto("https://www.idx.co.id/", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=60000)
            except Exception:
                pass
        except Exception as e:
            # navigation failed (possible proxy connection error); if we launched with proxy, retry without proxy
            print("Page navigation failed (possible proxy issue):", e)
            try:
                browser.close()
            except Exception:
                pass
            # relaunch without proxy and continue
            try:
                browser = _launch_ctx(headless, None)
                context = browser.new_context(locale="id-ID")
                page = context.new_page()
                page.goto("https://www.idx.co.id/", timeout=60000)
            except Exception as e2:
                print("Retry without proxy also failed:", e2)
                raise

        # If an auth token is provided, inject it into localStorage so client-side
        # requests that rely on localStorage-auth will include it.
        if auth_token:
            try:
                # write exact value as provided (expecting 'Bearer ...')
                page.evaluate(
                    "(t) => { localStorage.setItem('auth._token.local', t); }",
                    auth_token,
                )
                if debug:
                    print("Injected auth token into localStorage")
            except Exception:
                pass

        # Perform a short probe to see if we already passed any JS challenge.
        probe_ok = False
        try:
            probe_url = (
                "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
                + f"?keyword={keywords[0] if keywords else ''}&indexFrom=0&pageSize=1&dateFrom={date_from}&dateTo={date_to}"
            )
            probe_text = page.evaluate(
                "(u) => fetch(u, {headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest','Referer':'https://www.idx.co.id/'}}).then(r=>r.text()).catch(()=>null)",
                probe_url,
            )
            if probe_text and probe_text.strip().startswith("{"):
                probe_ok = True
        except Exception:
            probe_ok = False

        # If running headless and probe failed (Cloudflare), fall back to headed mode and ask user to solve challenge
        if not probe_ok and headless:
            print(
                "Headless probe returned a challenge; relaunching browser in headed mode so you can solve it."
            )
            try:
                browser.close()
            except Exception:
                pass
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context(
                locale="id-ID",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36",
            )
            page = context.new_page()
            page.goto("https://www.idx.co.id/", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)
            print(
                "Browser opened in headed mode. If a Cloudflare challenge appears, please solve it in the opened window."
            )
            input("Press Enter after you've completed any challenge in the browser...")
            # after user signals, poll the probe endpoint until we get JSON or timeout
            probe_ok2 = False
            import time

            for _ in range(30):
                try:
                    probe_text = page.evaluate(
                        "(u) => fetch(u, {headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest','Referer':'https://www.idx.co.id/'}}).then(r=>r.text()).catch(()=>null)",
                        probe_url,
                    )
                    if probe_text and probe_text.strip().startswith("{"):
                        probe_ok2 = True
                        break
                except Exception:
                    pass
                print("Waiting for challenge to clear... (retrying)")
                time.sleep(2)

            if not probe_ok2:
                print(
                    "Warning: probe still returns non-JSON after waiting. You can keep the browser open and rerun with --interactive to troubleshoot manually."
                )

        if debug and keywords:
            print(
                "Performed initial navigation; context cookies:", len(context.cookies())
            )

        for kw in keywords:
            print("Browser fetching (automated):", kw)
            api_url = (
                "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
                + f"?keyword={kw}&indexFrom=0&pageSize=100&dateFrom={date_from}&dateTo={date_to}"
            )
            # Prefer using Playwright's APIRequest via the browser context (shares cookies and low-level
            # networking) which often succeeds where page.evaluate fetch gets an HTML challenge.
            import time

            headers = {
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.idx.co.id/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            }

            data = {}
            text = None

            request_obj = getattr(context, "request", None)
            # If an auth token was provided, prefer page.evaluate fetch which can
            # read localStorage (auth._token.local) and allow client-side JS to
            # include the token in requests. Otherwise prefer context.request.
            # prefer page.evaluate when either an explicit auth_token was provided
            # or the loaded storage state contains an auth token in cookies/localStorage
            prefer_page_eval = bool(auth_token)
            try:
                if not prefer_page_eval and storage_state_obj:
                    # check cookies
                    for c in storage_state_obj.get("cookies", []):
                        if c.get("name") == "auth._token.local":
                            prefer_page_eval = True
                            break
                if not prefer_page_eval and storage_state_obj:
                    for origin in storage_state_obj.get("origins", []):
                        for kv in origin.get("localStorage", []):
                            if kv.get("name") == "auth._token.local":
                                prefer_page_eval = True
                                break
                        if prefer_page_eval:
                            break
            except Exception:
                # best-effort only
                pass
            if not prefer_page_eval and request_obj is not None:
                # use context.request which shares storage state and cookies
                for attempt in range(3):
                    try:
                        resp = request_obj.get(api_url, headers=headers)
                        text = resp.text()
                    except Exception as e:
                        print("  request attempt", attempt + 1, "error:", e)
                        text = None
                    if not text:
                        time.sleep(1)
                        continue

                    stripped = text.strip()
                    if stripped.startswith("{") or stripped.startswith("["):
                        try:
                            data = json.loads(text)
                            break
                        except Exception as e:
                            print("  json parse error:", e)
                            data = {}
                            break
                    else:
                        excerpt = (
                            (stripped[:400] + "...")
                            if len(stripped) > 400
                            else stripped
                        )
                        print(
                            "  non-json response (likely HTML/Cloudflare). excerpt:",
                            excerpt,
                        )
                        time.sleep(2)
                        continue
            else:
                # Use page.evaluate-based fetch (may pick up localStorage auth token)
                for attempt in range(3):
                    try:
                        text = page.evaluate(
                            "(u) => fetch(u, {headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest','Referer':'https://www.idx.co.id/'} , credentials: 'include'}).then(r=>r.text())",
                            api_url,
                        )
                    except Exception as e:
                        print("  fetch attempt", attempt + 1, "error:", e)
                        text = None
                    if not text:
                        time.sleep(1)
                        continue
                    stripped = text.strip()
                    if stripped.startswith("{") or stripped.startswith("["):
                        try:
                            data = json.loads(text)
                            break
                        except Exception as e:
                            print("  json parse error:", e)
                            data = {}
                            break
                    else:
                        excerpt = (
                            (stripped[:400] + "...")
                            if len(stripped) > 400
                            else stripped
                        )
                        print(
                            "  non-json response (likely HTML/Cloudflare). excerpt:",
                            excerpt,
                        )
                        time.sleep(2)
                        continue

            replies = data.get("Replies") or []
            for r in replies:
                peng = r.get("pengumuman") or r.get("Pengumuman") or {}
                kode = (peng.get("Kode_Emiten") or r.get("Kode_Emiten") or "").strip()
                judul = (
                    peng.get("JudulPengumuman") or peng.get("Judul_Pengumuman") or ""
                ).strip()
                tanggal = (
                    peng.get("TglPengumuman") or peng.get("Tanggal") or ""
                ).strip()
                key = (kode, judul, tanggal)
                if not kode and not judul:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "Kode_Emiten": kode,
                        "Judul_Pengumuman": judul,
                        "Tanggal_Pengumuman": tanggal,
                    }
                )

        # Save storage state for reuse
        try:
            ss = context.storage_state()
            DEFAULT_STORAGE_STATE.write_text(json.dumps(ss, indent=2), encoding="utf-8")
            cookie_dump = {"cookies": ss.get("cookies", [])}
            DEFAULT_COOKIE_EXPORT.write_text(
                json.dumps(cookie_dump, indent=2), encoding="utf-8"
            )
            print(f"Saved Playwright storage state to {DEFAULT_STORAGE_STATE}")
        except Exception as e:
            print("Failed saving storage state:", e)

        browser.close()

    # sort by date desc
    rows.sort(key=lambda r: parse_date(r.get("Tanggal_Pengumuman") or ""), reverse=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Kode_Emiten", "Judul_Pengumuman", "Tanggal_Pengumuman"],
            delimiter=";",
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return len(rows)


def requests_fetch_all(
    keywords: List[str],
    output_path: Path,
    session: Optional[requests.Session],
    max_pages: int,
) -> int:
    rows: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()

    from datetime import datetime, timedelta

    # thread-through date_from/date_to via outer args on call; if None, default to last 2 days
    # (main() will pass args.date_from/args.date_to)
    if not getattr(requests_fetch_all, "_injected_date_from", None) or not getattr(
        requests_fetch_all, "_injected_date_to", None
    ):
        today = datetime.now().date()
        default_to = today.strftime("%Y%m%d")
        default_from = (today - timedelta(days=2)).strftime("%Y%m%d")
        injected_from = (
            getattr(requests_fetch_all, "_injected_date_from", None) or default_from
        )
        injected_to = (
            getattr(requests_fetch_all, "_injected_date_to", None) or default_to
        )
    else:
        injected_from = getattr(requests_fetch_all, "_injected_date_from")
        injected_to = getattr(requests_fetch_all, "_injected_date_to")

    date_from = injected_from
    date_to = injected_to

    for kw in keywords:
        print("Requests fetching:", kw)
        try:
            replies = fetch_replies_for_keyword(
                kw,
                date_from=date_from,
                date_to=date_to,
                page_size=10000,
                session=session,
            )
        except Exception as e:
            print("  fetch error:", e)
            replies = []

        for r in replies:
            peng = r.get("Pengumuman") or r.get("pengumuman") or {}
            kode = (peng.get("Kode_Emiten") or r.get("Kode_Emiten") or "").strip()
            judul = (
                peng.get("JudulPengumuman") or peng.get("Judul_Pengumuman") or ""
            ).strip()
            tanggal = (peng.get("TglPengumuman") or peng.get("Tanggal") or "").strip()
            key = (kode, judul, tanggal)
            if not kode and not judul:
                continue
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "Kode_Emiten": kode,
                    "Judul_Pengumuman": judul,
                    "Tanggal_Pengumuman": tanggal,
                }
            )

    # sort by date desc
    rows.sort(key=lambda r: parse_date(r.get("Tanggal_Pengumuman") or ""), reverse=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Kode_Emiten", "Judul_Pengumuman", "Tanggal_Pengumuman"],
            delimiter=";",
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return len(rows)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Export IDX announcements for DEFAULT_KEYWORDS"
    )
    p.add_argument("--output", "-o", required=True, help="Output CSV path")
    p.add_argument(
        "--interactive",
        action="store_true",
        help="Open headed Playwright browser to allow manual challenge solving and capture cookies",
    )
    p.add_argument(
        "--automated-playwright",
        action="store_true",
        help="Use Playwright to automatically fetch all keywords via the browser (no manual interaction)",
    )
    p.add_argument(
        "--headless",
        action="store_true",
        help="When used with --automated-playwright, run browser in headless mode (default true).",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="(debug) print a short API probe result when using interactive",
    )
    p.add_argument(
        "--cookie", help="Provide raw Cookie header string to populate session cookies"
    )
    p.add_argument(
        "--storage-state",
        help=f"Path to Playwright storageState JSON to load/save (default: {DEFAULT_STORAGE_STATE})",
    )
    p.add_argument(
        "--export-cookies",
        help=f"Path to write cookie JSON (default: {DEFAULT_COOKIE_EXPORT})",
    )
    p.add_argument(
        "--max-pages", type=int, default=3, help="Max pages (unused in browser mode)"
    )
    p.add_argument(
        "--date-from",
        help="Override start date (inclusive) in YYYYMMDD format. Default = today - 2 days.",
    )
    p.add_argument(
        "--date-to",
        help="Override end date (inclusive) in YYYYMMDD format. Default = today.",
    )
    p.add_argument(
        "--auth-token",
        help="Optional Authorization token (include 'Bearer ...') to inject into localStorage and request headers",
    )
    p.add_argument(
        "--proxy",
        help="Optional HTTP(S) proxy URL to use for requests and Playwright, e.g. http://user:pass@host:port or host:port. Also supports IDX_PROXY env var.",
    )
    p.add_argument(
        "--persist-login",
        action="store_true",
        help="When using --automated-playwright, attempt an interactive login automatically (headed) if stored Playwright storage state is missing or appears expired. Uses --login-email/--login-password or IDX_AUTH_EMAIL/IDX_AUTH_PASSWORD env vars.",
    )
    p.add_argument(
        "--show-sample",
        type=int,
        default=0,
        help="After writing CSV, print first N rows to stdout for quick inspection",
    )
    p.add_argument(
        "--login",
        action="store_true",
        help="Perform an interactive login to idx.co.id with provided credentials and save Playwright storage state",
    )
    p.add_argument("--login-email", help="Email for automated login")
    p.add_argument("--login-password", help="Password for automated login")
    p.add_argument(
        "--save-credentials",
        action="store_true",
        help="Store provided --login-email and --login-password in the OS keyring (optional)",
    )
    p.add_argument(
        "--keyring-service",
        default="idx-scraper",
        help="Keyring service name to store credentials under (default: idx-scraper)",
    )
    args = p.parse_args()

    out = Path(args.output)
    # proxy from CLI or env
    proxy_url = args.proxy or os.environ.get("IDX_PROXY")

    # validate optional date overrides (YYYYMMDD)
    def _valid_date(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        try:
            datetime.strptime(s, "%Y%m%d")
            return s
        except Exception:
            raise SystemExit(f"Invalid date format for {s}; expected YYYYMMDD")

    user_date_from = _valid_date(args.date_from)
    user_date_to = _valid_date(args.date_to)
    session = None
    if args.cookie:
        session = session_from_cookie_header(args.cookie)
    # If a storage state path is provided or default exists, try to load it into a requests.Session
    storage_path = (
        Path(args.storage_state) if args.storage_state else DEFAULT_STORAGE_STATE
    )
    if session is None:
        loaded = session_from_storage_state(storage_path)
        if loaded is not None:
            session = loaded
            print(f"Loaded cookies from storage state: {storage_path}")
    # If we have a proxy, configure requests session proxies
    if proxy_url:
        try:
            if session is None:
                session = requests.Session()
            # apply same proxy to http and https
            if not proxy_url.startswith("http"):
                proxy_url = "http://" + proxy_url
            session.proxies.update({"http": proxy_url, "https": proxy_url})
            print(f"Configured requests to use proxy: {proxy_url}")
        except Exception as e:
            print("Failed to configure proxy for requests:", e)

    if args.interactive:
        n = browser_fetch_all(
            DEFAULT_KEYWORDS,
            out,
            debug=args.debug,
            date_from=user_date_from,
            date_to=user_date_to,
            proxy_url=proxy_url,
        )
        # if --export-cookies supplied, copy the default cookie export to that path
        if args.export_cookies:
            try:
                dst = Path(args.export_cookies)
                dst.write_text(
                    DEFAULT_COOKIE_EXPORT.read_text(encoding="utf-8"), encoding="utf-8"
                )
                print(f"Exported cookies to {dst}")
            except Exception as e:
                print("Failed to export cookies to --export-cookies:", e)
        print(f"Wrote {n} rows to {out}")
        return
    if args.automated_playwright:
        # headless flag means run headless when provided
        headless = True if args.headless else False
        # allow environment-based credentials as fallback
        env_email = os.environ.get("IDX_AUTH_EMAIL")
        env_password = os.environ.get("IDX_AUTH_PASSWORD")
        env_token = os.environ.get("IDX_AUTH_TOKEN")
        # if user asked to persist-login and no good storage state exists, try to login interactively
        if args.persist_login:
            need_login = False
            # If storage state is missing or doesn't contain auth token, perform login
            try:
                if not storage_path.exists() or not storage_state_has_auth(
                    storage_path
                ):
                    need_login = True
            except Exception:
                need_login = True

            if need_login:
                # prefer CLI args, then env, then keyring (if available)
                login_email = args.login_email or env_email
                login_password = args.login_password or env_password
                if (not login_email or not login_password) and keyring:
                    try:
                        stored_email = keyring.get_password(
                            args.keyring_service, "email"
                        )
                        stored_password = keyring.get_password(
                            args.keyring_service, "password"
                        )
                        if stored_email and stored_password:
                            login_email = login_email or stored_email
                            login_password = login_password or stored_password
                    except Exception:
                        pass
                # If credentials still missing, in interactive shells offer to run the
                # local .env helper (scripts/create_env.py) so the user can create
                # a .env containing IDX_AUTH_EMAIL/IDX_AUTH_PASSWORD. In CI/cron we
                # must fail fast.
                if not login_email or not login_password:
                    helper = (
                        Path(__file__).resolve().parent / "scripts" / "create_env.py"
                    )
                    if sys.stdin.isatty() and helper.exists():
                        try:
                            resp = (
                                input(
                                    "Credentials not provided. Create a local .env now? [y/N]: "
                                )
                                .strip()
                                .lower()
                            )
                        except Exception:
                            resp = "n"
                        if resp in ("y", "yes"):
                            try:
                                rc = subprocess.call([sys.executable, str(helper)])
                                if rc == 0:
                                    # reload .env if python-dotenv is available
                                    try:
                                        from dotenv import load_dotenv

                                        load_dotenv(override=False)
                                    except Exception:
                                        pass
                                    # pick up newly written env vars
                                    login_email = login_email or os.environ.get(
                                        "IDX_AUTH_EMAIL"
                                    )
                                    login_password = login_password or os.environ.get(
                                        "IDX_AUTH_PASSWORD"
                                    )
                            except Exception:
                                pass
                    if not login_email or not login_password:
                        raise SystemExit(
                            "--persist-login requires credentials via --login-email/--login-password or IDX_AUTH_EMAIL/IDX_AUTH_PASSWORD env vars"
                        )
                ok = perform_interactive_login_and_save(
                    login_email,
                    login_password,
                    storage_path,
                    proxy_url=proxy_url,
                    headless=True,
                )
                if not ok:
                    raise SystemExit("Interactive login for persist-login failed")

        # If running headless in automated mode and user did NOT request persist-login,
        # make a fail-fast check: if storage state does not exist or lacks auth token,
        # exit with a distinct non-zero code so CI/cron can detect and trigger remediation.
        if headless and not args.persist_login:
            try:
                if not storage_path.exists() or not storage_state_has_auth(
                    storage_path
                ):
                    print(
                        "ERROR: headless automated run requires a valid storage state with auth token.\n"
                        "Use --persist-login to perform an interactive login/update storage, or provide credentials via env/--login-email and --login-password."
                    )
                    sys.exit(2)
            except Exception:
                print(
                    "ERROR: failed to validate storage state; refusing to run headless to avoid silent failures."
                )
                sys.exit(2)

        # choose token precedence: CLI arg > ENV
        auth_token = args.auth_token or env_token
        n = playwright_automated_fetch_all(
            DEFAULT_KEYWORDS,
            out,
            headless=headless,
            debug=args.debug,
            date_from=user_date_from,
            date_to=user_date_to,
            auth_token=auth_token,
            proxy_url=proxy_url,
        )
        print(f"Wrote {n} rows to {out}")
        return

    # If --login requested, perform an interactive login using Playwright and save storage state
    if args.login:
        email = args.login_email or os.environ.get("IDX_AUTH_EMAIL")
        password = args.login_password or os.environ.get("IDX_AUTH_PASSWORD")
        if (not email or not password) and keyring:
            try:
                stored_email = keyring.get_password(args.keyring_service, "email")
                stored_password = keyring.get_password(args.keyring_service, "password")
                if stored_email and stored_password:
                    email = email or stored_email
                    password = password or stored_password
            except Exception:
                pass
        if not email or not password:
            raise SystemExit(
                "--login requires --login-email and --login-password (or keyring-stored creds)"
            )

        ok = perform_interactive_login_and_save(
            email, password, storage_path, proxy_url=proxy_url
        )
        if not ok:
            raise SystemExit("Login failed")
        # Optionally persist credentials to keyring
        if args.save_credentials and keyring:
            try:
                keyring.set_password(args.keyring_service, "email", email)
                keyring.set_password(args.keyring_service, "password", password)
                print(f"Saved credentials to keyring service '{args.keyring_service}'")
            except Exception as e:
                print("Failed saving credentials to keyring:", e)
        print("Login flow complete. Re-run exporter to use saved state.")
        return

    # inject dates into requests_fetch_all for non-browser mode
    setattr(requests_fetch_all, "_injected_date_from", user_date_from)
    setattr(requests_fetch_all, "_injected_date_to", user_date_to)

    n = requests_fetch_all(
        DEFAULT_KEYWORDS, out, session=session, max_pages=args.max_pages
    )
    print(f"Wrote {n} rows to {out}")


if __name__ == "__main__":
    main()
