"""Watch Shaw Theatres for showtimes of target movies and alert via Telegram."""

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

# Movie title keyword (case-insensitive) -> None (any date) or "YYYY-MM-DD" (only that date).
TARGETS = {
    "dune": None,
    "sunrise on the reaping": None,
    "wildwood": "2026-11-07",
    "avengers: doomsday": None,
}

# Optional filters (case-insensitive substring match). None = no filter.
BRAND = None   # e.g. "IMAX"
VENUE = None   # e.g. "Jewel"

# Scan start for undated targets that aren't in Shaw's coming-soon list (else: today).
FALLBACK_START = {
    "sunrise on the reaping": "2026-11-19",
}

DAYS_TO_SCAN = 14   # for undated targets: days to check from the scan start
PREVIEW_DAYS = 3    # start this many days before a coming-soon release date

API = "https://snow-pwsm-legacy.sice.tech"
SEEN_FILE = Path("seen.json")
SGT = timezone(timedelta(hours=8))


def get(path, **params):
    r = requests.get(f"{API}/{path}", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response from {path} {params}: {data}")
    return data


def match(title):
    title = title.lower()
    return next((k for k in TARGETS if k in title), None)


def dates_to_query(coming_soon, today):
    release = {}
    for m in coming_soon:
        k = match(m["primaryTitle"])
        if k and m.get("releaseDate"):
            d = date.fromisoformat(m["releaseDate"][:10])
            release[k] = min(d, release.get(k, d))
    dates = set()
    for k, target in TARGETS.items():
        if target:
            if date.fromisoformat(target) >= today:
                dates.add(target)
        else:
            if k in release:
                start = release[k] - timedelta(PREVIEW_DAYS)
            else:
                start = date.fromisoformat(FALLBACK_START.get(k, today.isoformat()))
            start = max(today, start)
            dates.update((start + timedelta(i)).isoformat() for i in range(DAYS_TO_SCAN))
    return sorted(dates)


def wanted(show, key):
    target = TARGETS[key]
    return (
        (target is None or show["displayDate"] == target)
        and (BRAND is None or BRAND.lower() in show["brandCode"].lower())
        and (VENUE is None or VENUE.lower() in show["locationVenueName"].lower())
    )


def send(text):
    token, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    # Telegram caps messages at 4096 chars; split on line boundaries.
    chunk = ""
    for line in text.splitlines(keepends=True):
        if len(chunk) + len(line) > 4000:
            post(token, chat, chunk)
            chunk = ""
        chunk += line
    if chunk:
        post(token, chat, chunk)


def post(token, chat, text):
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()


def main():
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    today = datetime.now(SGT).date()
    new_keys, lines = [], []

    coming_soon = get("get_coming_soon_movies")
    for m in coming_soon:
        if match(m["primaryTitle"]) and f"cs:{m['movieReleaseId']}" not in seen:
            new_keys.append(f"cs:{m['movieReleaseId']}")
            lines.append(f"🍿 Coming soon at Shaw: {m['primaryTitle']} (release {m['releaseDate'][:10]})")

    for d in dates_to_query(coming_soon, today):
        for m in get("get_show_times", date=d):
            key = match(m["primaryTitle"])
            if not key:
                continue
            for s in m["showTimes"]:
                pid = str(s["performanceId"])
                if pid in seen or pid in new_keys or not wanted(s, key):
                    continue
                new_keys.append(pid)
                lines.append(
                    f"🎬 {m['primaryTitle']} | {s['brandCode']} | {s['locationVenueName']} | "
                    f"{s['displayDate']} {s['displayTime']}"
                )

    print(f"{len(lines)} new alert(s)")
    if lines:
        send("\n".join(lines) + "\n\nBook: https://shaw.sg/")
        SEEN_FILE.write_text(json.dumps(sorted(seen | set(new_keys))))
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
