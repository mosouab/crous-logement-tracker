"""
Scrapes /tools/42/search, iterates all pages, and returns a list of
Accommodation dicts filtered by the configured LOCATIONS.
"""

import json
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from config import (
    BASE_URL, SEARCH_URL, COOKIES_FILE, LOCATIONS, MAX_PRICE, USE_AUTH
)

_auth_warning_sent = False  # send only once per process run


def _is_logged_in(soup: BeautifulSoup) -> bool:
    """Return False if the page still shows the login button (cookies expired/invalid)."""
    login_link = soup.select_one('a[href="/mse/discovery/connect"]')
    return login_link is None

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)

    if USE_AUTH:
        from auth import ensure_cookies_file
        ensure_cookies_file()
        try:
            with open(COOKIES_FILE, encoding="utf-8") as f:
                cookies = json.load(f)
            for c in cookies:
                session.cookies.set(c["name"], c["value"], domain=c.get("domain"))
            print("🔐 Using saved login cookies.")
        except FileNotFoundError:
            print(f"⚠️  {COOKIES_FILE} not found — falling back to anonymous mode.")

    return session


def _get_total_pages(soup: BeautifulSoup) -> int:
    """Extract total page count from the <title> tag."""
    title = soup.find("title")
    if title:
        match = re.search(r"page \d+ sur (\d+)", title.text)
        if match:
            return int(match.group(1))
    return 1


def _parse_price(text: str) -> float | None:
    """Return the lowest price found in a price string, or None."""
    numbers = re.findall(r"[\d,]+(?:\.\d+)?", text.replace(",", ".").replace("\xa0", ""))
    values = [float(n) for n in numbers if float(n) > 0]
    return min(values) if values else None


def _parse_cards(soup: BeautifulSoup) -> list[dict]:
    accommodations = []
    for card in soup.select("li.fr-col-lg-4"):
        title_tag = card.select_one("h3.fr-card__title a")
        if not title_tag:
            continue

        name = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        acc_id = href.rstrip("/").split("/")[-1]
        url = f"{BASE_URL}{href}"

        address_tag = card.select_one("p.fr-card__desc")
        address = address_tag.get_text(strip=True) if address_tag else ""

        price_tag = card.select_one(".fr-badges-group .fr-badge")
        price_str = price_tag.get_text(strip=True) if price_tag else ""

        img_tag = card.select_one(".fr-card__img img.fr-responsive-img")
        image_url = img_tag.get("src") if img_tag else None
        if image_url and image_url.startswith("/"):
            image_url = f"{BASE_URL}{image_url}"

        accommodations.append({
            "id": acc_id,
            "name": name,
            "address": address,
            "price": price_str,
            "price_min": _parse_price(price_str),
            "url": url,
            "image_url": image_url,
        })
    return accommodations


def _matches_location(accommodation: dict) -> bool:
    if not LOCATIONS:
        return True
    addr_upper = accommodation["address"].upper()
    return any(loc in addr_upper for loc in LOCATIONS)


def _matches_price(accommodation: dict) -> bool:
    if MAX_PRICE is None:
        return True
    price_min = accommodation.get("price_min")
    if price_min is None:
        return True
    return price_min <= MAX_PRICE


def fetch_all_accommodations() -> list[dict]:
    global _auth_warning_sent
    session = _build_session()
    all_results: list[dict] = []

    # Fetch page 1 first to determine total pages
    resp = session.get(SEARCH_URL, params={"page": 1}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser", from_encoding="utf-8")

    # Detect expired/invalid cookies
    if USE_AUTH and not _is_logged_in(soup):
        if not _auth_warning_sent:
            from telegram_bot import send_message
            send_message(
                "⚠️ <b>CROUS Notifier</b>: Login cookies have expired or are invalid.\n"
                "Falling back to <b>anonymous mode</b> (fewer listings visible).\n\n"
                "Run <code>python main.py --login</code> to re-authenticate."
            )
            _auth_warning_sent = True
        print("⚠️  Cookies invalid — running in anonymous mode.")

    total_pages = _get_total_pages(soup)
    all_results.extend(_parse_cards(soup))

    for page in range(2, total_pages + 1):
        time.sleep(random.uniform(0.5, 2.0))  # polite delay
        resp = session.get(SEARCH_URL, params={"page": page}, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser", from_encoding="utf-8")
        all_results.extend(_parse_cards(soup))

    filtered = [a for a in all_results if _matches_location(a) and _matches_price(a)]
    return filtered


def _extract_city(address: str) -> str | None:
    """Extract city name from an address string like '47000 AGEN' → 'AGEN'."""
    m = re.search(r'\d{5}\s+(.+)$', address.strip())
    return m.group(1).strip() if m else None


def get_all_cities() -> list[str]:
    """Fetch all listing pages and return a sorted list of unique city names."""
    session = _build_session()
    cities: set[str] = set()

    resp = session.get(SEARCH_URL, params={"page": 1}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser", from_encoding="utf-8")
    total_pages = _get_total_pages(soup)

    for card in soup.select("li.fr-col-lg-4"):
        addr_tag = card.select_one("p.fr-card__desc")
        if addr_tag:
            city = _extract_city(addr_tag.get_text(strip=True))
            if city:
                cities.add(city)

    for page in range(2, total_pages + 1):
        time.sleep(random.uniform(0.3, 1.0))
        resp = session.get(SEARCH_URL, params={"page": page}, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser", from_encoding="utf-8")
        for card in soup.select("li.fr-col-lg-4"):
            addr_tag = card.select_one("p.fr-card__desc")
            if addr_tag:
                city = _extract_city(addr_tag.get_text(strip=True))
                if city:
                    cities.add(city)

    return sorted(cities)
