# CROUS Notifier — Copilot Instructions

## Setup & Running

```bash
pip install -r requirements.txt

# First time only (if using logged-in mode):
python main.py --login       # opens browser, complete login, saves cookies.json

# Start the notifier:
python main.py               # polls on schedule per CHECK_INTERVAL_MINUTES
```

Config lives in `.env` (copy from `.env.example`). State is persisted in `state.json` (auto-created).

## Architecture

Single-process Python polling loop. No framework — just `schedule` + `requests`.

```
main.py        CLI entry point. --login triggers auth.py; otherwise runs the loop.
auth.py        Playwright (headed) browser login → cookies.json. One-time use.
scraper.py     GET /tools/42/search?page=N with requests. Parses HTML (BeautifulSoup).
               Iterates all pages. Filters results by LOCATIONS and MAX_PRICE locally.
notifier.py    Diffs current scraped IDs vs state.json. Sends Telegram alert per new listing.
               On first run (empty state), seeds state without alerting.
telegram_bot.py  asyncio.run() wrapper around python-telegram-bot send_message.
state.py       Loads/saves known accommodation IDs as a JSON array in state.json.
config.py      Reads .env via python-dotenv. All other modules import from here.
```

## Key Conventions

- **Location filtering is local**: The CROUS search URL `?location=` param does not reliably filter by freetext. All pages are scraped and filtered in Python by matching `LOCATIONS` values (uppercased) against the address string of each card.
- **Authentication is opt-in**: `USE_AUTH=false` (default) → anonymous scraping of public listings. `USE_AUTH=true` → attaches cookies from `cookies.json` to every request, showing DSE-eligible listings.
- **First run seeds silently**: If `state.json` is empty/missing, `check_and_notify()` saves current listings without sending any Telegram messages (avoids spamming on first launch).
- **Accommodation ID**: Extracted from the URL path `/tools/42/accommodations/{id}`. This is the stable identity used for deduplication.
- **Scraping is polite**: Random 0.5–2s delay between page requests in `scraper.py`.

## .env Reference

| Key | Default | Description |
|-----|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | required | From @BotFather |
| `TELEGRAM_CHAT_ID` | required | Your Telegram user/chat ID |
| `LOCATIONS` | required | Comma-separated city names, e.g. `Evry,Paris` |
| `CHECK_INTERVAL_MINUTES` | `10` | Poll interval |
| `MAX_PRICE` | _(none)_ | Optional max rent (euros) |
| `USE_AUTH` | `false` | `true` to use saved cookies |
