import json
import os
import requests as req
from datetime import datetime
from config import STATE_FILE, HEROKU_API_KEY, HEROKU_APP_NAME


def _heroku_headers() -> dict:
    return {
        "Authorization": f"Bearer {HEROKU_API_KEY}",
        "Accept": "application/vnd.heroku+json; version=3",
        "Content-Type": "application/json",
    }


def _heroku_pull() -> None:
    """On startup: download STATE_JSON config var → state.json (only if missing)."""
    if not HEROKU_API_KEY or not HEROKU_APP_NAME or os.path.exists(STATE_FILE):
        return
    try:
        r = req.get(
            f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/config-vars",
            headers=_heroku_headers(),
            timeout=10,
        )
        r.raise_for_status()
        raw = r.json().get("STATE_JSON", "")
        if raw:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                f.write(raw)
    except Exception as e:
        print(f"⚠️  Could not pull state from Heroku: {e}")


def _heroku_push(payload: str) -> None:
    """After every save: upload state.json content to Heroku STATE_JSON config var."""
    if not HEROKU_API_KEY or not HEROKU_APP_NAME:
        return
    try:
        req.patch(
            f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/config-vars",
            headers=_heroku_headers(),
            json={"STATE_JSON": payload},
            timeout=10,
        )
    except Exception as e:
        print(f"⚠️  Could not push state to Heroku: {e}")


# Pull from Heroku on first import (no-op when running locally)
_heroku_pull()


def _load_raw() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        # Migrate old format (list of IDs) to new format (dict of id -> accommodation)
        if isinstance(data, list):
            return {acc_id: {"id": acc_id} for acc_id in data}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_state() -> set[str]:
    return set(_load_raw().keys())


def load_listings() -> list[dict]:
    """Return all tracked accommodations sorted by first_seen (newest first)."""
    raw = _load_raw()
    listings = list(raw.values())
    listings.sort(key=lambda x: x.get("first_seen", ""), reverse=True)
    return listings


def save_state(known_ids: set[str], current_accommodations: list[dict] | None = None) -> None:
    existing = _load_raw()
    if current_accommodations:
        by_id = {a["id"]: a for a in current_accommodations}
        for acc_id in known_ids:
            if acc_id in by_id:
                entry = dict(by_id[acc_id])
                # Preserve original first_seen if already stored
                if acc_id in existing and "first_seen" in existing[acc_id]:
                    entry["first_seen"] = existing[acc_id]["first_seen"]
                else:
                    entry["first_seen"] = datetime.now().isoformat(timespec="seconds")
                existing[acc_id] = entry
            elif acc_id not in existing:
                existing[acc_id] = {"id": acc_id}
    else:
        for acc_id in known_ids:
            if acc_id not in existing:
                existing[acc_id] = {"id": acc_id}

    payload = json.dumps(existing, indent=2, ensure_ascii=False)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(payload)
    _heroku_push(payload)
