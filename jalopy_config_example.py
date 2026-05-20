# jalopy_config.py — DO NOT COMMIT
# Copy this file to jalopy_config.py and fill in your values.

BASE_URL       = "https://inventory.pickapartjalopyjungle.com"
CHECK_INTERVAL = (82800, 90000)   # 23–25 hours in seconds (randomized daily)

NTFY_CHANNEL = ""   # e.g. "jalopy-monitor-abc123" — leave blank to skip

YARDS = {
    "Boise":       1020,
    "Caldwell":    1021,
    "Garden City": 1119,
    "Nampa":       1022,
    "Twin Falls":  1099,
}

# Subset of YARDS keys to actually poll — remove any you don't care about
YARDS_TO_MONITOR = ["Boise", "Caldwell", "Garden City", "Nampa", "Twin Falls"]

USERS = [
    {
        "name": "User1",
        "discord_webhook": "",          # your private Discord channel webhook URL
        "watchlist": [
            # make/model must match the uppercase strings the site uses
            # set model to None to match any model for that make
            {"make": "TOYOTA",    "model": "PICKUP",  "year_min": 1979, "year_max": 1995},
            {"make": "FORD",      "model": "MUSTANG", "year_min": 1965, "year_max": 1973},
            {"make": "CHEVROLET", "model": None,      "year_min": 1955, "year_max": 1972},
        ],
    },
    {
        "name": "User2",
        "discord_webhook": "",          # friend's private Discord channel webhook URL
        "watchlist": [
            # TBD
        ],
    },
]
