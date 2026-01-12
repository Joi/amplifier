#!/usr/bin/env python3
"""
Sync Withings weight data to health-tracker.

Calls the health-tracker Withings sync API endpoint.
Can be run manually or via launchd/periodic runner.

Usage:
    python sync_withings.py           # Sync last 1 day (default)
    python sync_withings.py --days 7  # Sync last 7 days
"""

import argparse
import os
import sys
from pathlib import Path

import httpx

# Health-tracker API endpoint
HEALTH_TRACKER_URL = os.environ.get("HEALTH_TRACKER_URL", "https://health.ito.com")
CRON_SECRET = os.environ.get("CRON_SECRET")


def sync_withings(days: int = 1) -> dict:
    """Trigger Withings sync via health-tracker API."""
    if not CRON_SECRET:
        # Try to load from secrets
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from amplifier.utils.secrets import get_secret

            cron_secret = get_secret(
                "cron_secret",
                "Amplifier Health Tracker Cron Secret",
                env_name="CRON_SECRET",
            )
        except Exception as e:
            print(f"Warning: Could not load CRON_SECRET: {e}")
            cron_secret = None
    else:
        cron_secret = CRON_SECRET

    url = f"{HEALTH_TRACKER_URL}/api/withings/sync"
    params = {"days": days}

    if cron_secret:
        params["secret"] = cron_secret

    try:
        response = httpx.post(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"Request failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Sync Withings data")
    parser.add_argument("--days", type=int, default=1, help="Days of history to sync")
    args = parser.parse_args()

    print(f"Syncing Withings data (last {args.days} day(s))...")

    try:
        result = sync_withings(days=args.days)
        synced = result.get("synced", 0)
        print(f"Success: synced {synced} measurement(s)")

        if result.get("results"):
            for r in result["results"][:5]:  # Show first 5
                print(f"  {r.get('action')}: {r.get('recorded_at', '')[:10]} - {r.get('weight')} kg")

        return 0
    except Exception as e:
        print(f"Sync failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
