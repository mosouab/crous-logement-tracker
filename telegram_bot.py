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
    use_auth = state.get("use_auth", False)
    logs = state.get("logs", [])

    try:
        tracked = len(load_listings())
    except Exception:
        tracked = listing_count

    last_str = last_check.strftime("%H:%M:%S") if last_check else "Never"
    locs = ", ".join(LOCATIONS) if LOCATIONS else "All cities"
    auth_str = "🔐 Logged-in" if use_auth else "👤 Anonymous"
    status_icon = "▶️" if running else "⏸"

    msg = (
        f"🤖 <b>CROUS Notifier Status</b>\n\n"
        f"{status_icon} <b>Running:</b> {'Yes' if running else 'No'}\n"
        f"🔍 <b>Last check:</b> {last_str}\n"
        f"⏱ <b>Interval:</b> every {CHECK_INTERVAL_MINUTES} min\n"
        f"📋 <b>Tracked listings:</b> {tracked}\n"
        f"🆕 <b>New since start:</b> {new_since}\n"
        f"📍 <b>Locations:</b> {locs}\n"
        f"{auth_str}"
    )

    if logs:
        log_lines = "\n".join(f"  {l}" for l in logs)
        msg += f"\n\n📜 <b>Recent logs:</b>\n<code>{log_lines}</code>"

    return msg


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
                text = (msg.get("text") or "").strip()
                if text.lower() == "logs":
                    try:
                        state = state_getter()
                        all_logs = state.get("logs_all") or state.get("logs", [])
                        if not all_logs:
                            replies = ["📜 No logs yet."]
                        else:
                            # Split into ≤4000-char chunks to stay within Telegram limit
                            lines = all_logs
                            chunks, current = [], []
                            size = 0
                            for line in lines:
                                if size + len(line) + 1 > 3800:
                                    chunks.append(current)
                                    current, size = [line], len(line)
                                else:
                                    current.append(line)
                                    size += len(line) + 1
                            if current:
                                chunks.append(current)
                            replies = [
                                f"📜 <b>Logs ({i+1}/{len(chunks)}):</b>\n<code>" + "\n".join(c) + "</code>"
                                for i, c in enumerate(chunks)
                            ]
                    except Exception as e:
                        replies = [f"⚠️ Could not retrieve logs: {e}"]
                else:
                    try:
                        replies = [_build_status_message(state_getter())]
                    except Exception as e:
                        replies = [f"⚠️ Could not retrieve status: {e}"]
                for reply in replies:
                    req.post(f"{url}/sendMessage", json={
                        "chat_id": TELEGRAM_CHAT_ID,
                        "text": reply,
                        "parse_mode": "HTML",
                    }, timeout=10)
        except Exception:
            _t.sleep(5)
