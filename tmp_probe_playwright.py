from playwright.sync_api import sync_playwright
import sys

token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlZWUxNmY1My03Yjg0LTQ0YTQtOTAwOC1iNGM1ZGM5NGRmYmMiLCJlbWFpbCI6ImRpY2t5MnV4QGdtYWlsLmNvbSIsImp0aSI6ImEzOGUxODdkLTJmMWQtNDkyZS05YTY4LWFlNTBmZDA5YTM5ZiIsInJvbGUiOiJNYXN5YXJha2F0IFVtdW0iLCJyb2xlSWQiOiJhY2I2NmFiMi05YjZiLTRkOTYtYTNlZC0xNTRhZGQ2MDRkMmIiLCJ1dCI6ImZhYjRmYWMxLWM1NDYtNDFkZS1hZWJjLWExNGRhNjg5NTcxNSIsIm5iZiI6MTc2MDM0NTQxNywiZXhwIjoxNzYwMzQ2NjE3LCJpYXQiOjE3NjAzNDU0MTd9.g_oQWw-O3KkRUlD4klfQ3nuVzhaqIKA6JU-0ZRo3Tug"
api_url = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement?keyword=&indexFrom=0&pageSize=1&dateFrom=20251011&dateTo=20251013"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(locale="id-ID", user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36")
    page = context.new_page()
    try:
        page.goto("https://www.idx.co.id/", timeout=60000)
    except Exception:
        pass
    # set localStorage token
    try:
        page.evaluate("(t) => { localStorage.setItem('auth._token.local', t); }", token)
        print('Set localStorage auth._token.local')
    except Exception as e:
        print('Failed setting localStorage:', e)

    # Try context.request with Authorization header
    try:
        req = context.request
        headers = {
            'Accept': 'application/json',
            'Authorization': token,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.idx.co.id/'
        }
        resp = req.get(api_url, headers=headers)
        print('context.request status:', resp.status)
        text = resp.text()
        print('response snippet (first 800 chars):')
        print(text[:800])
    except Exception as e:
        print('context.request error:', e)

    # Try page.evaluate fetch which may use localStorage token in app JS
    try:
        fetch_script = "(u) => fetch(u, {headers:{'Accept':'application/json','X-Requested-With':'XMLHttpRequest','Referer':'https://www.idx.co.id/'}}).then(r=>r.text()).catch(e=>String(e))"
        text2 = page.evaluate(fetch_script, api_url)
        print('page.evaluate fetch snippet (first 800 chars):')
        print((text2 or '')[:800])
    except Exception as e:
        print('page.evaluate fetch error:', e)

    # save modified storage state to temp file for inspection
    try:
        ss = context.storage_state()
        import json
        open('tmp_probe_storage_state.json','w',encoding='utf-8').write(json.dumps(ss,indent=2))
        print('Wrote tmp_probe_storage_state.json')
    except Exception as e:
        print('Failed writing storage state:', e)

    browser.close()
