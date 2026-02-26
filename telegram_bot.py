import asyncio
import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_message(text: str, image_url: str | None = None) -> None:
    async def _send() -> None:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        if image_url:
            try:
                await bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=image_url,
                    caption=text,
                    parse_mode="HTML",
                )
                return
            except Exception:
                pass  # fall back to text-only
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    asyncio.run(_send())


def _build_status_message(state: dict) -> str:
    from config import LOCATIONS, CHECK_INTERVAL_MINUTES
    from state import load_listings

    running = state.get("running", False)
    last_check = state.get("last_check")
    listing_count = state.get("listing_count", 0)
    new_since = state.get("new_since_start", 0)

    try:
        tracked = len(load_listings())
    except Exception:
        tracked = listing_count

    last_str = last_check.strftime("%H:%M:%S") if last_check else "Never"
    locs = ", ".join(LOCATIONS) if LOCATIONS else "All cities"

    status_icon = "▶️" if running else "⏸"
    return (
        f"🤖 <b>CROUS Notifier Status</b>\n\n"
        f"{status_icon} <b>Running:</b> {'Yes' if running else 'No'}\n"
        f"🔍 <b>Last check:</b> {last_str}\n"
        f"⏱ <b>Interval:</b> every {CHECK_INTERVAL_MINUTES} min\n"
        f"📋 <b>Tracked listings:</b> {tracked}\n"
        f"🆕 <b>New since start:</b> {new_since}\n"
        f"📍 <b>Locations:</b> {locs}"
    )


def start_status_bot(state_getter) -> None:
    """Poll Telegram for messages and reply with status. Uses plain HTTP — no asyncio."""
    import requests as req
    import time as _t

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    offset = 0

    # Skip updates that arrived before we started (drop_pending)
    try:
        r = req.get(f"{url}/getUpdates", params={"offset": -1}, timeout=10)
        updates = r.json().get("result", [])
        if updates:
            offset = updates[-1]["update_id"] + 1
    except Exception:
        pass

    while True:
        try:
            r = req.get(
                f"{url}/getUpdates",
                params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=35,
            )
            r.raise_for_status()
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg:
                    continue
                if str(msg.get("chat", {}).get("id", "")) != str(TELEGRAM_CHAT_ID):
                    continue
                try:
                    status = _build_status_message(state_getter())
                except Exception as e:
                    status = f"⚠️ Could not retrieve status: {e}"
                req.post(f"{url}/sendMessage", json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": status,
                    "parse_mode": "HTML",
                }, timeout=10)
        except Exception:
            _t.sleep(5)
