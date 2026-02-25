"""
Flask web interface for controlling the CROUS Notifier.
Runs the polling loop in a background thread.

Usage:
    python main.py --web
Then open: http://localhost:5000
"""

import os
import threading
import time
import schedule as sched
from collections import deque
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from functools import wraps

from config import STATE_FILE, WEB_PASSWORD, PORT

app = Flask(__name__)
app.secret_key = os.urandom(24)


def _require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not WEB_PASSWORD:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or auth.password != WEB_PASSWORD:
            return Response(
                "Authentication required.",
                401,
                {"WWW-Authenticate": 'Basic realm="CROUS Notifier"'},
            )
        return f(*args, **kwargs)
    return decorated

# ── Shared state ────────────────────────────────────────────────────────────
_lock = threading.Lock()
_logs: deque[str] = deque(maxlen=100)
_state = {
    "running": False,
    "last_check": None,       # datetime or None
    "listing_count": 0,
    "new_since_start": 0,
}
_stop_event = threading.Event()
_thread: threading.Thread | None = None


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    with _lock:
        _logs.appendleft(f"[{ts}] {msg}")


# ── Patched notifier that writes to our log ─────────────────────────────────
def _run_check() -> None:
    import scraper as sc
    from state import load_state, save_state
    from telegram_bot import send_message
    from notifier import _format_message

    _log("🔍 Checking for new accommodations…")
    try:
        current = sc.fetch_all_accommodations()
    except Exception as e:
        _log(f"❌ Scrape failed: {e}")
        return

    known_ids = load_state()
    current_ids = {a["id"] for a in current}

    with _lock:
        _state["last_check"] = datetime.now()
        _state["listing_count"] = len(current_ids)

    if not known_ids:
        _log(f"📋 First run: storing {len(current_ids)} listings (no alerts sent).")
        save_state(current_ids, current)
        return

    new_items = [a for a in current if a["id"] not in known_ids]
    if new_items:
        _log(f"🆕 {len(new_items)} new listing(s) found!")
        for acc in new_items:
            try:
                send_message(_format_message(acc), image_url=acc.get("image_url"))
                _log(f"  ✅ Notified: {acc['name']} — {acc['address']}")
            except Exception as e:
                _log(f"  ❌ Telegram failed for {acc['name']}: {e}")
        with _lock:
            _state["new_since_start"] += len(new_items)
        save_state(known_ids | current_ids, current)
    else:
        _log(f"✓ No new listings. ({len(current_ids)} tracked)")


def _polling_loop(interval_minutes: int) -> None:
    _run_check()
    sched.every(interval_minutes).minutes.do(_run_check)
    while not _stop_event.is_set():
        sched.run_pending()
        time.sleep(10)
    sched.clear()
    _log("⏹ Notifier stopped.")


# ── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
@_require_auth
def index():
    from state import load_state
    with _lock:
        state_copy = dict(_state)
        logs_copy = list(_logs)
    try:
        known_count = len(load_state())
    except Exception:
        known_count = 0
    env = _read_env()
    return render_template(
        "index.html",
        state=state_copy,
        logs=logs_copy,
        known_count=known_count,
        env=env,
    )


@app.route("/start", methods=["POST"])
@_require_auth
def start():
    global _thread, _stop_event
    with _lock:
        if _state["running"]:
            flash("Notifier is already running.", "warning")
            return redirect(url_for("index"))

    from dotenv import load_dotenv
    load_dotenv(override=True)
    import importlib, config, scraper
    importlib.reload(config)
    importlib.reload(scraper)

    _stop_event = threading.Event()
    interval = int(_read_env().get("CHECK_INTERVAL_MINUTES", "10") or "10")
    _thread = threading.Thread(target=_polling_loop, args=(interval,), daemon=True)
    _thread.start()

    with _lock:
        _state["running"] = True
        _state["new_since_start"] = 0
    _log(f"▶ Notifier started (every {interval} min).")
    flash("Notifier started.", "success")
    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
@_require_auth
def stop():
    with _lock:
        if not _state["running"]:
            flash("Notifier is not running.", "warning")
            return redirect(url_for("index"))
    _stop_event.set()
    with _lock:
        _state["running"] = False
    flash("Notifier stopped.", "success")
    return redirect(url_for("index"))


@app.route("/check-now", methods=["POST"])
@_require_auth
def check_now():
    threading.Thread(target=_run_check, daemon=True).start()
    flash("Manual check triggered.", "success")
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
@_require_auth
def settings():
    if request.method == "POST":
        new_env = {
            "TELEGRAM_BOT_TOKEN": request.form.get("TELEGRAM_BOT_TOKEN", "").strip(),
            "TELEGRAM_CHAT_ID": request.form.get("TELEGRAM_CHAT_ID", "").strip(),
            "LOCATIONS": request.form.get("LOCATIONS", "").strip(),
            "CHECK_INTERVAL_MINUTES": request.form.get("CHECK_INTERVAL_MINUTES", "10").strip(),
            "MAX_PRICE": request.form.get("MAX_PRICE", "").strip(),
            "USE_AUTH": request.form.get("USE_AUTH", "false"),
        }
        _write_env(new_env)
        flash("Settings saved. Restart the notifier to apply changes.", "success")
        return redirect(url_for("index"))
    return redirect(url_for("index"))


@app.route("/logs")
@_require_auth
def logs_json():
    with _lock:
        return {"logs": list(_logs)}


@app.route("/listings")
@_require_auth
def listings_json():
    from state import load_listings
    return {"listings": load_listings()}


# ── .env helpers ─────────────────────────────────────────────────────────────
def _read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    try:
        with open(".env", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env


def _write_env(values: dict[str, str]) -> None:
    lines = []
    try:
        with open(".env", encoding="utf-8") as f:
            existing = f.readlines()
    except FileNotFoundError:
        existing = []

    written = set()
    for line in existing:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            lines.append(line.rstrip("\n"))
            continue
        k = stripped.split("=", 1)[0].strip()
        if k in values:
            lines.append(f"{k}={values[k]}")
            written.add(k)
        else:
            lines.append(line.rstrip("\n"))

    for k, v in values.items():
        if k not in written:
            lines.append(f"{k}={v}")

    with open(".env", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
