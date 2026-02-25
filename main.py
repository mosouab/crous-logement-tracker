"""
CROUS Notifier — entry point

Usage:
    python main.py --login     Run interactive browser login and save cookies.
                               Then set USE_AUTH=true in .env to use them.

    python main.py             Start the polling loop (uses .env config).

    python main.py --web       Start the web control interface at http://localhost:5000
"""

import os
import argparse
import schedule
import time

from config import CHECK_INTERVAL_MINUTES, USE_AUTH
from notifier import check_and_notify


def main() -> None:
    parser = argparse.ArgumentParser(description="CROUS dorm availability notifier")
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open browser for one-time CROUS login and save session cookies.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the web control interface at http://localhost:5000",
    )
    args = parser.parse_args()

    if args.login:
        from auth import login_and_save_cookies
        login_and_save_cookies()
        return

    if args.web:
        from web import app
        from config import PORT
        host = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"
        print(f"🌐 Web interface running at http://{host}:{PORT}")
        print("Press Ctrl+C to stop.\n")
        app.run(host=host, port=PORT, debug=False)
        return

    mode = "logged-in" if USE_AUTH else "anonymous"
    print(f"🚀 CROUS Notifier started (mode: {mode}, interval: {CHECK_INTERVAL_MINUTES} min)")
    print("Press Ctrl+C to stop.\n")

    # Run once immediately, then on schedule
    check_and_notify()
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_and_notify)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
