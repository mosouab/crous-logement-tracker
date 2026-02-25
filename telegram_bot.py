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
