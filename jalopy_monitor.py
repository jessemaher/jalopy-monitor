#!/usr/bin/env python3
"""
Jalopy Jungle Inventory Monitor
Watches Jalopy Jungle junkyard yards for new vehicle arrivals and sends
personalized Discord DMs + shared Ntfy push notification + Mac notification
when a watched vehicle appears.
"""

import json
import random
import subprocess
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from jalopy_config import BASE_URL, CHECK_INTERVAL, NTFY_CHANNEL, YARDS, YARDS_TO_MONITOR, USERS

SNAPSHOT_FILE = Path(__file__).parent / "jalopy_snapshot.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL + "/",
}


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

def notify_mac(title: str, message: str, sound: str = "Glass"):
    """Send a native macOS notification with sound (local only)."""
    script = (
        f'display notification "{message}" '
        f'with title "{title}" '
        f'sound name "{sound}"'
    )
    subprocess.run(["osascript", "-e", script], check=False)


def notify_ntfy(title: str, message: str, ntfy_priority: str = "default"):
    """Send a shared push notification via Ntfy."""
    if not NTFY_CHANNEL:
        print("  📱 Ntfy skipped (channel not configured)")
        return
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_CHANNEL}",
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": ntfy_priority,
                "Tags": "car",
            },
            timeout=10
        )
        print("  📱 Ntfy notification sent")
    except Exception as e:
        print(f"  ⚠️  Ntfy failed: {e}")


def notify_discord(webhook_url: str, title: str, message: str, color: int):
    """Send a personalized Discord embed message via webhook."""
    if not webhook_url:
        return
    try:
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
            }]
        }
        requests.post(webhook_url, json=payload, timeout=10)
        print("  💬 Discord notification sent")
    except Exception as e:
        print(f"  ⚠️  Discord failed: {e}")


def send_system_alert(title: str, message: str, ntfy_priority: str = "high"):
    """Send a system-level alert (errors, unexpected conditions) via all channels."""
    notify_mac(title, message, sound="Basso")
    notify_ntfy(title, message, ntfy_priority=ntfy_priority)
    for user in USERS:
        notify_discord(user["discord_webhook"], title, message, 15158332)


# ─────────────────────────────────────────────
# PERSISTENCE
# ─────────────────────────────────────────────

def load_snapshot() -> dict:
    """
    Load the last-seen vehicle snapshot from disk.
    Returns a dict keyed by '{yard_id}:{make}', values are lists of
    [year, make, model, row] lists. Returns {} if the file does not exist.
    """
    if SNAPSHOT_FILE.exists():
        return json.loads(SNAPSHOT_FILE.read_text())
    return {}


def save_snapshot(snapshot: dict):
    """Persist the current snapshot to disk. Overwrites the previous file entirely."""
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2))


# ─────────────────────────────────────────────
# SCRAPING
# ─────────────────────────────────────────────

def fetch_vehicles(yard_id: int, make: str) -> list:
    """
    POST to the inventory site for a specific yard and vehicle make.
    Returns a list of (year, make, model, row) tuples parsed from the HTML table.
    Raises requests.RequestException on HTTP errors.
    """
    resp = requests.post(
        BASE_URL + "/",
        data={"YardId": yard_id, "VehicleMake": make},
        headers=HEADERS,
        timeout=15,
    )

    if resp.status_code == 403:
        raise requests.RequestException(f"403 Forbidden for yard={yard_id} make={make}")
    if resp.status_code == 429:
        raise requests.RequestException(f"429 Rate Limited for yard={yard_id} make={make}")

    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    vehicles = []

    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) == 4:
            year, v_make, model, row_num = (c.get_text(strip=True) for c in cells)
            vehicles.append((year, v_make, model, row_num))

    return vehicles


# ─────────────────────────────────────────────
# MATCHING
# ─────────────────────────────────────────────

def build_fetch_plan() -> dict:
    """
    Compute the deduplicated set of (yard_id, make) pairs to fetch,
    mapped to the list of users watching that combination.
    Returns {(yard_id, make): [user_dict, ...]}.
    """
    plan = {}
    for yard_name in YARDS_TO_MONITOR:
        yard_id = YARDS[yard_name]
        for user in USERS:
            for entry in user["watchlist"]:
                key = (yard_id, entry["make"])
                plan.setdefault(key, [])
                if user not in plan[key]:
                    plan[key].append(user)
    return plan


def matches_watchlist_entry(vehicle: tuple, entry: dict) -> bool:
    """
    Returns True if (year, make, model, row) satisfies {make, model, year_min, year_max}.
    model=None in the entry matches any vehicle model.
    Returns False if the year is non-numeric.
    """
    year, v_make, v_model, _ = vehicle
    try:
        v_year = int(year)
    except ValueError:
        return False

    if entry["model"] is not None and v_model != entry["model"]:
        return False

    return entry["year_min"] <= v_year <= entry["year_max"]


def find_matching_entries(vehicle: tuple, user: dict) -> list:
    """Return all watchlist entries for this user that match the vehicle."""
    return [e for e in user["watchlist"] if matches_watchlist_entry(vehicle, e)]


# ─────────────────────────────────────────────
# NOTIFICATION FORMATTING
# ─────────────────────────────────────────────

def format_vehicle_message(vehicle: tuple, yard_name: str, matching_entries: list) -> str:
    """Build a human-readable notification body for a single vehicle."""
    year, make, model, row_num = vehicle
    match_lines = []
    for e in matching_entries:
        model_part = e["model"] if e["model"] else "any model"
        match_lines.append(f"Matches: {e['year_min']}–{e['year_max']} {make} {model_part}")

    lines = [
        f"{year} {make} {model} — Row {row_num}",
        f"Yard: {yard_name}",
        *match_lines,
        BASE_URL + "/",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# MAIN CHECK CYCLE
# ─────────────────────────────────────────────

def run_check_cycle(snapshot: dict) -> dict:
    """
    One full poll: for each (yard_id, make) in the fetch plan,
    fetch current vehicles, diff against snapshot, notify users with matches,
    and return the updated snapshot.
    """
    fetch_plan = build_fetch_plan()
    yard_name_by_id = {v: k for k, v in YARDS.items()}

    for (yard_id, make), interested_users in fetch_plan.items():
        yard_name = yard_name_by_id[yard_id]
        key = f"{yard_id}:{make}"
        prev_vehicles = {tuple(v) for v in snapshot.get(key, [])}

        print(f"  Checking {yard_name} — {make}...")
        try:
            current_vehicles = fetch_vehicles(yard_id, make)
        except requests.RequestException as e:
            err = str(e)
            if "403" in err:
                send_system_alert("⚠️ Jalopy Monitor", f"Blocked (403) — {yard_name} {make}")
            elif "429" in err:
                send_system_alert("⚠️ Jalopy Monitor", f"Rate limited (429) — backing off 5 min")
                time.sleep(300)
            else:
                print(f"    ⚠️  Fetch error: {e}")
            continue

        current_set = {tuple(v) for v in current_vehicles}
        new_vehicles = current_set - prev_vehicles

        if not current_vehicles and prev_vehicles:
            send_system_alert(
                "⚠️ Jalopy Monitor",
                f"Zero results for {yard_name} {make} — site may have changed!"
            )

        if new_vehicles:
            print(f"    🚨 {len(new_vehicles)} new vehicle(s) at {yard_name}!")

        for vehicle in new_vehicles:
            year, v_make, v_model, row_num = vehicle
            print(f"    → {year} {v_make} {v_model} (Row {row_num})")

            for user in interested_users:
                matching = find_matching_entries(vehicle, user)
                if not matching:
                    continue

                msg = format_vehicle_message(vehicle, yard_name, matching)
                notify_discord(
                    user["discord_webhook"],
                    f"New Vehicle at {yard_name} Jalopy Jungle",
                    msg,
                    5763719,  # green
                )
                print(f"      → {user['name']}: notified")

            # Shared notifications for any new vehicle that matched at least one user
            any_match = any(find_matching_entries(vehicle, u) for u in interested_users)
            if any_match:
                shared_msg = f"{year} {v_make} {v_model} at {yard_name} (Row {row_num})"
                notify_mac("🚗 New Vehicle — Jalopy Jungle", shared_msg, sound="Ping")
                notify_ntfy("🚗 New Vehicle — Jalopy Jungle", shared_msg)

        # Replace snapshot entry wholesale (snapshot semantics — vehicles leave yards)
        snapshot[key] = [list(v) for v in current_set]
        time.sleep(random.uniform(1, 3))

    return snapshot


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  Jalopy Jungle Inventory Monitor")
    print("=" * 50)

    snapshot = load_snapshot()
    print(f"\nLoaded snapshot with {len(snapshot)} tracked yard/make pairs.")

    while True:
        print("\nStarting check cycle...")
        try:
            snapshot = run_check_cycle(snapshot)
            save_snapshot(snapshot)
            print("  ✅ Cycle complete. Snapshot saved.")
        except Exception as e:
            print(f"  ❌ Unexpected error in check cycle: {e}")

        interval = random.randint(*CHECK_INTERVAL)
        hours = interval / 3600
        print(f"  Sleeping {hours:.1f}h until next check...")
        time.sleep(interval)


if __name__ == "__main__":
    main()
