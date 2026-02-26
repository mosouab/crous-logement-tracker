import asyncio
import threading
import telegram
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
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
    """Run Telegram bot polling in the calling thread (designed for a daemon thread)."""
    async def _handle(update: Update, context) -> None:
        # Only respond to the configured chat
        if str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
            return
        try:
            msg = _build_status_message(state_getter())
        except Exception as e:
            msg = f"⚠️ Could not retrieve status: {e}"
        await update.message.reply_text(msg, parse_mode="HTML")

    async def _run() -> None:
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(MessageHandler(filters.ALL, _handle))
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        # keep running until the thread is killed (daemon)
        stop = asyncio.Event()
        await stop.wait()

    asyncio.run(_run())
