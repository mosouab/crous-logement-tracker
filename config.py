import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

LOCATIONS: list[str] = [
    loc.strip().upper()
    for loc in os.getenv("LOCATIONS", "").split(",")
    if loc.strip()
]

CHECK_INTERVAL_MINUTES: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))

_max_price = os.getenv("MAX_PRICE", "").strip()
MAX_PRICE: int | None = int(_max_price) if _max_price else None

USE_AUTH: bool = os.getenv("USE_AUTH", "false").strip().lower() == "true"

COOKIES_FILE = "cookies.json"
STATE_FILE = "state.json"
BASE_URL = "https://trouverunlogement.lescrous.fr"
SEARCH_URL = f"{BASE_URL}/tools/42/search"

# Heroku — set these to persist state/cookies across dyno restarts
HEROKU_API_KEY: str = os.getenv("HEROKU_API_KEY", "")
HEROKU_APP_NAME: str = os.getenv("HEROKU_APP_NAME", "")

# Web UI password (required when deployed; optional locally)
WEB_PASSWORD: str = os.getenv("WEB_PASSWORD", "")

# Port for the web server (Heroku sets this automatically)
PORT: int = int(os.getenv("PORT", "5000"))
