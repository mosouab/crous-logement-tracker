"""
One-time interactive login via Playwright.
Saves session cookies to cookies.json so subsequent scraping
can use them with the requests library.

On Heroku: run --login locally, then upload cookies.json content
as the COOKIES_JSON config var:
    heroku config:set COOKIES_JSON="$(cat cookies.json)" -a YOUR_APP_NAME

Usage:
    python main.py --login
"""

import json
import os
from config import BASE_URL, COOKIES_FILE, HEROKU_API_KEY, HEROKU_APP_NAME


def _write_cookies_to_heroku(payload: str) -> None:
    if not HEROKU_API_KEY or not HEROKU_APP_NAME:
        return
    try:
        import requests as req
        req.patch(
            f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/config-vars",
            headers={
                "Authorization": f"Bearer {HEROKU_API_KEY}",
                "Accept": "application/vnd.heroku+json; version=3",
                "Content-Type": "application/json",
            },
            json={"COOKIES_JSON": payload},
            timeout=10,
        )
        print("☁️  Cookies also uploaded to Heroku config var COOKIES_JSON.")
    except Exception as e:
        print(f"⚠️  Could not push cookies to Heroku: {e}")


def ensure_cookies_file() -> None:
    """If cookies.json is missing, try to restore it from COOKIES_JSON env var."""
    if os.path.exists(COOKIES_FILE):
        return
    raw = os.getenv("COOKIES_JSON", "").strip()
    if raw:
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(raw)


def login_and_save_cookies() -> None:
    from playwright.sync_api import sync_playwright
    print("Opening browser for login — please complete the authentication in the browser window.")
    print("The browser will close automatically once you are logged in.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(f"{BASE_URL}/mse/discovery/connect")

        # Wait until the user is redirected back to the CROUS site after login
        page.wait_for_url(f"{BASE_URL}/**", timeout=300_000)

        cookies = context.cookies()
        browser.close()

    payload = json.dumps(cookies, indent=2)
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write(payload)

    print(f"✅ Cookies saved to {COOKIES_FILE}")
    print("Set USE_AUTH=true in your .env to use them.")
    _write_cookies_to_heroku(payload)
