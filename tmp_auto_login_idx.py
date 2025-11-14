from playwright.sync_api import sync_playwright
import json

EMAIL = "yourname@email.com"
PASSWORD = "PASSWORD_HERE"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(locale="id-ID")
    page = context.new_page()
    page.goto("https://www.idx.co.id/", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000)
    print("Opened idx.co.id homepage")

    # Try to find a login link/button - this site may use a modal or route
    # Common selectors to try
    login_selectors = [
        "text=Login",
        "a:has-text('Login')",
        "button:has-text('Login')",
        "text=Masuk",
        "a:has-text('Masuk')",
    ]

    clicked = False
    for sel in login_selectors:
        try:
            el = page.query_selector(sel)
            if el:
                el.click()
                clicked = True
                print("Clicked login selector:", sel)
                break
        except Exception:
            continue

    # If nothing clicked, try navigating directly to a common auth URL
    if not clicked:
        # try common auth routes
        for url in [
            "https://www.idx.co.id/id-ID/login",
            "https://www.idx.co.id/login",
            "https://www.idx.co.id/Account/Login",
        ]:
            try:
                page.goto(url, timeout=10000)
                page.wait_for_load_state("networkidle", timeout=10000)
                print("Navigated to", url)
                break
            except Exception:
                continue

    # Wait a little for any login form to appear
    page.wait_for_timeout(2000)

    # Try to fill common form fields
    tried = False
    try:
        if page.query_selector('input[type="email"]'):
            page.fill('input[type="email"]', EMAIL)
            tried = True
        elif page.query_selector('input[name="email"]'):
            page.fill('input[name="email"]', EMAIL)
            tried = True
        elif page.query_selector('input[name="username"]'):
            page.fill('input[name="username"]', EMAIL)
            tried = True
    except Exception:
        pass

    try:
        if page.query_selector('input[type="password"]'):
            page.fill('input[type="password"]', PASSWORD)
            tried = True
        elif page.query_selector('input[name="password"]'):
            page.fill('input[name="password"]', PASSWORD)
            tried = True
    except Exception:
        pass

    if tried:
        # Try submit buttons
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
                    print("Clicked submit button:", bsel)
                    break
            except Exception:
                continue

    print("Waiting after submit...")
    page.wait_for_timeout(5000)

    # Save storage state
    ss = context.storage_state()
    open("playwright_storage_state.json", "w", encoding="utf-8").write(
        json.dumps(ss, indent=2)
    )
    print("Saved playwright_storage_state.json")

    # Probe API
    probe_url = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement?keyword=&indexFrom=0&pageSize=1&dateFrom=20251011&dateTo=20251013"
    try:
        text = page.evaluate(
            "(u) => fetch(u, {headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest','Referer':'https://www.idx.co.id/'} , credentials: 'include'}).then(r=>r.text()).catch(()=>null)",
            probe_url,
        )
        print("Probe returned (first 400 chars):")
        print((text or "")[:400])
    except Exception as e:
        print("Probe failed:", e)

    browser.close()
