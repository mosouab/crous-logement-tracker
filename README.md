# CROUS Notifier

Watches [trouverunlogement.lescrous.fr](https://trouverunlogement.lescrous.fr) for new student housing listings and sends instant Telegram alerts. Deployable to Heroku.

## Features

- Polls CROUS for new listings on a configurable interval
- Sends Telegram notifications with name, address, price, and link
- Filters by city and optional max rent
- Web UI to view tracked listings, live logs, and settings
- Telegram bot: send any message to get system status, send `Logs` to get full log history
- Supports anonymous scraping or logged-in mode (via saved cookies)

## Setup

### 1. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the **token**
2. Message [@userinfobot](https://t.me/userinfobot) → copy your **chat ID**

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
LOCATIONS=Paris,Evry          # cities to monitor (comma-separated)
CHECK_INTERVAL_MINUTES=10
MAX_PRICE=                    # optional rent cap in €
USE_AUTH=false
WEB_PASSWORD=choose_a_password
```

### 3. Run locally

```bash
pip install -r requirements.txt
python main.py --web           # starts web UI + notifier
```

Web UI is available at `http://localhost:5000`.

## Logged-in mode

Logged-in sessions may see more listings. To enable:

1. Install Playwright: `pip install playwright && playwright install chromium`
2. Run `python main.py --login` — a browser window opens, log in to CROUS, then close it
3. Cookies are saved to `cookies.json` and auto-pushed to Heroku (if `HEROKU_API_KEY` is set)
4. Set `USE_AUTH=true` in settings or `.env`

> Cookies expire periodically. Re-run `--login` when you see scrape errors.

## Telegram bot commands

| Message | Response |
|---------|----------|
| Anything | System status (uptime, last check, listings, auth mode, recent logs) |
| `Logs` | Full log history (last 100 lines) |

## Deploy to Heroku

### Prerequisites

- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
- Docker installed locally

### Steps

```bash
heroku create your-app-name
heroku stack:set container --app your-app-name

heroku config:set \
  TELEGRAM_BOT_TOKEN=... \
  TELEGRAM_CHAT_ID=... \
  LOCATIONS=Paris \
  CHECK_INTERVAL_MINUTES=10 \
  WEB_PASSWORD=... \
  USE_AUTH=false \
  --app your-app-name

git push heroku master
```

Add `HEROKU_API_KEY` and `HEROKU_APP_NAME` to your local `.env` so `--login` can push cookies to Heroku automatically.

### Refreshing cookies on Heroku

```bash
python main.py --login   # logs in locally and auto-pushes cookies to Heroku
heroku ps:restart --app your-app-name
```

## Project structure

```
main.py          – CLI entrypoint (--web, --login, --run)
web.py           – Flask app, routes, background polling loop
scraper.py       – CROUS website scraper
notifier.py      – Compares listings, sends Telegram alerts
state.py         – Persists seen listings (state.json)
auth.py          – Cookie login via Playwright
telegram_bot.py  – send_message() + status bot
config.py        – All configuration via env vars
cities.txt       – 200+ French cities for the city selector
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Your Telegram user ID |
| `LOCATIONS` | ✅ | — | Comma-separated cities to monitor |
| `CHECK_INTERVAL_MINUTES` | | `10` | Polling frequency |
| `MAX_PRICE` | | none | Max rent filter in € |
| `USE_AUTH` | | `false` | Use saved login cookies |
| `WEB_PASSWORD` | | — | Password for web UI |
| `HEROKU_API_KEY` | | — | For pushing cookies to Heroku |
| `HEROKU_APP_NAME` | | — | Your Heroku app name |
