# movie-watcher

Checks Shaw Theatres every 5 minutes (GitHub Actions) and sends a Telegram alert when a target movie shows up in Shaw's coming-soon list or gets showtimes.

## Setup

1. **Create a Telegram bot:** message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token.
2. **Get your chat ID:** send your bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `message.chat.id`.
3. **Add repo secrets** (Settings → Secrets and variables → Actions): `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`.
4. **Push**, then run it once from the Actions tab (**watch → Run workflow**) to check it works.

## Configure

Edit the top of `watcher.py`:

```python
TARGETS = {
    "dune": None,                       # any date
    "sunrise on the reaping": "2026-11-21",  # only this date
}
BRAND = "IMAX"   # or None
VENUE = "Jewel"  # or None
```

Keywords match anywhere in the title, ignoring case. For targets with no date, the watcher checks 14 days. The window starts 3 days before the release date in Shaw's coming-soon list (to catch previews). If the movie isn't listed there, it starts from the movie's `FALLBACK_START` date, or from today if there isn't one.

## Notes

- Repeat alerts are prevented by `seen.json` (performance IDs plus coming-soon entries), which is kept between runs with `actions/cache`. To get every alert again, delete the `seen-*` caches under Actions → Caches.
- GitHub can delay scheduled runs, and it turns off scheduled workflows after 60 days with no repo activity.
- Run locally: `pip install -r requirements.txt && TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... python watcher.py`
