#!/usr/bin/env python3
"""
Sync Withings weight data to health-tracker database.

Uses direct Withings API integration (from amplifier-bundle-gtd) which
supports age-encrypted secrets. No external service dependency.

Usage:
    python sync_withings.py           # Sync last 1 day (default)
    python sync_withings.py --days 7  # Sync last 7 days
"""

import argparse
import importlib.util
import sys
from pathlib import Path


def load_withings_module():
    """Load withings.py directly without importing the full package."""
    withings_path = (
        Path.home()
        / "amplifier-bundle-gtd"
        / "modules"
        / "tool-gtd"
        / "amplifier_module_tool_gtd"
        / "withings.py"
    )

    if not withings_path.exists():
        raise FileNotFoundError(f"Withings module not found at {withings_path}")

    spec = importlib.util.spec_from_file_location("withings", withings_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="Sync Withings data")
    parser.add_argument("--days", type=int, default=1, help="Days of history to sync")
    args = parser.parse_args()

    print(f"Syncing Withings data (last {args.days} day(s))...")

    try:
        withings = load_withings_module()
        result = withings.sync_weight(days=args.days)
    except Exception as e:
        print(f"Failed to load/run Withings sync: {e}")
        return 1

    if not result.get("success"):
        print(f"Sync failed: {result.get('error', 'Unknown error')}")
        return 1

    synced = result.get("synced", 0)
    message = result.get("message", f"Synced {synced} measurement(s)")
    print(f"Success: {message}")

    if result.get("results"):
        for r in result["results"][:5]:  # Show first 5
            action = r.get("action", "synced")
            date = r.get("recorded_at", "")[:10]
            weight = r.get("weight", "?")
            print(f"  {action}: {date} - {weight} kg")

    return 0


if __name__ == "__main__":
    sys.exit(main())
