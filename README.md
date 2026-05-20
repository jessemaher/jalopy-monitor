# Jalopy Jungle Inventory Monitor

Watches Jalopy Jungle junkyard locations across Idaho for new vehicle arrivals. When a vehicle matching your watchlist appears, you get a personalized Discord notification and a shared push notification via [ntfy](https://ntfy.sh).

## Features

- Monitors all five Idaho Jalopy Jungle yards (Boise, Caldwell, Garden City, Nampa, Twin Falls)
- Per-user watchlists: filter by make, model, and year range
- Personalized Discord DMs per user via webhook
- Shared push notifications via ntfy.sh
- Native macOS notification support
- Checks once daily (randomized 23–25 hour interval)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Copy the example config and fill in your values:

```bash
cp jalopy_config_example.py jalopy_config.py
```

Edit `jalopy_config.py`:

```python
NTFY_CHANNEL = "your-ntfy-channel"   # leave blank to skip

USERS = [
    {
        "name": "YourName",
        "discord_webhook": "https://discord.com/api/webhooks/...",
        "watchlist": [
            {"make": "TOYOTA", "model": "PICKUP", "year_min": 1979, "year_max": 1995},
            {"make": "FORD",   "model": None,     "year_min": 1965, "year_max": 1973},
        ],
    },
]
```

Set `model` to `None` to match any model for that make. Make and model strings must be uppercase, matching what the Jalopy Jungle site uses (e.g. `"TOYOTA"`, `"PICKUP"`).

### 3. Run

```bash
python jalopy_monitor.py
```

The first run builds a baseline snapshot of current inventory and begins the daily loop. You won't receive alerts until the second cycle when new arrivals can be detected.

## Testing notifications

To trigger a notification immediately, delete `jalopy_snapshot.json` after the first run and run again — everything currently at the yards that matches your watchlist will fire as new.

## Multiple users

Add additional entries to the `USERS` list in your config. Each user gets their own Discord notification only for vehicles matching their watchlist. The ntfy and macOS notifications are shared and fire for any match across all users.

## Yard locations

| Yard | ID |
|---|---|
| Boise | 1020 |
| Caldwell | 1021 |
| Garden City | 1119 |
| Nampa | 1022 |
| Twin Falls | 1099 |

To monitor only specific yards, edit `YARDS_TO_MONITOR` in your config.
