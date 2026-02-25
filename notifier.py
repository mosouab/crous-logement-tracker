"""
Core logic: fetch current listings, compare with stored state,
send Telegram alerts for any new accommodations, then update state.
"""

from scraper import fetch_all_accommodations
from state import load_state, save_state, load_listings
from telegram_bot import send_message


def _format_message(acc: dict) -> str:
    return (
        f"🏠 <b>Nouveau logement CROUS disponible !</b>\n\n"
        f"📍 <b>{acc['name']}</b>\n"
        f"{acc['address']}\n"
        f"💶 {acc['price']}\n"
        f"🔗 <a href=\"{acc['url']}\">Voir le logement</a>"
    )


def check_and_notify() -> None:
    print("🔍 Checking for new accommodations...")

    try:
        current = fetch_all_accommodations()
    except Exception as e:
        print(f"❌ Scrape failed: {e}")
        return

    known_ids = load_state()
    current_ids = {a["id"] for a in current}

    if not known_ids:
        # First run — seed state without sending notifications
        print(f"📋 First run: storing {len(current_ids)} known accommodations (no alerts sent).")
        save_state(current_ids, current)
        return

    new_accommodations = [a for a in current if a["id"] not in known_ids]

    if new_accommodations:
        print(f"🆕 {len(new_accommodations)} new accommodation(s) found! Sending notifications...")
        for acc in new_accommodations:
            try:
                send_message(_format_message(acc), image_url=acc.get("image_url"))
                print(f"  ✅ Notified: {acc['name']} — {acc['address']}")
            except Exception as e:
                print(f"  ❌ Telegram send failed for {acc['name']}: {e}")
        save_state(known_ids | current_ids, current)
    else:
        print(f"✓ No new accommodations. ({len(current_ids)} listings tracked)")
