#!/usr/bin/env python3
"""
Withings weight sync - direct API integration.

Uses age-based secret decryption (SSH-compatible, no keychain/1password required).
Connects directly to Withings API and Supabase for token/data storage.
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import httpx

# Withings measure types
MEASURE_TYPES = {
    "WEIGHT": 1,  # kg
    "FAT_RATIO": 6,  # %
    "MUSCLE_MASS": 76,  # kg
}

# Cache for decrypted secrets (avoid repeated age calls)
_secrets_cache: dict[str, str] = {}


def get_age_secret(key: str) -> str | None:
    """Get a secret from age-encrypted file (no keychain/1password).

    This is the preferred auth method for SSH and automation contexts.
    """
    if key in _secrets_cache:
        return _secrets_cache[key]

    age_file = Path.home() / "dotfiles-private" / "amplifier-secrets.env.age"
    age_key = Path.home() / ".config" / "age" / "secrets.key"

    if not age_file.exists() or not age_key.exists():
        return None

    try:
        result = subprocess.run(
            ["age", "-d", "-i", str(age_key), str(age_file)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        # Parse all secrets into cache
        for line in result.stdout.splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                _secrets_cache[k] = v.strip().strip('"').strip("'")

        return _secrets_cache.get(key)
    except Exception:
        return None


def get_secret(key: str) -> str | None:
    """Get secret with fallback chain: env var -> age file."""
    if value := os.environ.get(key):
        return value
    return get_age_secret(key)


def _get_supabase_client() -> tuple[str, dict[str, str]]:
    """Get Supabase URL and headers for API calls."""
    # Use health-tracker's Supabase instance
    supabase_url = "https://liomxpsyjkpzpiquwslq.supabase.co"
    service_key = get_secret("HEALTH_TRACKER_SERVICE_ROLE_KEY")

    if not service_key:
        raise ValueError("HEALTH_TRACKER_SERVICE_ROLE_KEY not found in secrets")

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    return supabase_url, headers


def _refresh_token_if_needed(
    token_data: dict, client: httpx.Client, supabase_url: str, headers: dict
) -> str:
    """Refresh Withings OAuth token if expiring soon."""
    expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))
    now = datetime.now(expires_at.tzinfo)

    # Refresh if token expires in less than 5 minutes
    if (expires_at - now).total_seconds() > 300:
        return token_data["access_token"]

    # Refresh the token
    client_id = get_secret("WITHINGS_CLIENT_ID")
    client_secret = get_secret("WITHINGS_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("WITHINGS_CLIENT_ID or WITHINGS_CLIENT_SECRET not found")

    response = client.post(
        "https://wbsapi.withings.net/v2/oauth2",
        data={
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": token_data["refresh_token"],
        },
    )

    data = response.json()
    if data.get("status") != 0:
        raise ValueError(f"Token refresh failed: {data}")

    body = data["body"]
    new_expires_at = datetime.fromtimestamp(
        time.time() + body["expires_in"]
    ).isoformat()

    # Update stored tokens in Supabase
    client.patch(
        f"{supabase_url}/rest/v1/withings_tokens",
        headers=headers,
        params={"user_id": "eq.default"},
        json={
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
            "expires_at": new_expires_at,
            "updated_at": datetime.now().isoformat(),
        },
    )

    return body["access_token"]


def sync_weight(days: int = 1) -> dict:
    """Sync weight measurements directly from Withings API.

    Args:
        days: Number of days to sync (default: 1)

    Returns:
        Dict with success status and sync results
    """
    try:
        supabase_url, headers = _get_supabase_client()
    except ValueError as e:
        return {"success": False, "error": str(e)}

    with httpx.Client(timeout=30.0) as client:
        # Get stored Withings tokens from Supabase
        response = client.get(
            f"{supabase_url}/rest/v1/withings_tokens",
            headers=headers,
            params={"user_id": "eq.default", "select": "*"},
        )

        if response.status_code != 200:
            return {"success": False, "error": f"Failed to get tokens: {response.text}"}

        tokens = response.json()
        if not tokens:
            return {
                "success": False,
                "error": "Withings not connected. Please authorize first via health-tracker.",
            }

        token_data = tokens[0]

        # Refresh token if needed
        try:
            access_token = _refresh_token_if_needed(
                token_data, client, supabase_url, headers
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # Calculate date range
        end_date = int(time.time())
        start_date = end_date - (days * 24 * 60 * 60)

        # Fetch measurements from Withings
        measure_response = client.post(
            "https://wbsapi.withings.net/measure",
            headers={"Authorization": f"Bearer {access_token}"},
            data={
                "action": "getmeas",
                "startdate": str(start_date),
                "enddate": str(end_date),
                "meastypes": f"{MEASURE_TYPES['WEIGHT']},{MEASURE_TYPES['FAT_RATIO']},{MEASURE_TYPES['MUSCLE_MASS']}",
            },
        )

        measure_data = measure_response.json()

        if measure_data.get("status") != 0:
            return {
                "success": False,
                "error": f"Withings API error: {measure_data}",
            }

        measure_groups = measure_data.get("body", {}).get("measuregrps", [])

        if not measure_groups:
            return {
                "success": True,
                "synced": 0,
                "results": [],
                "message": "No new weight measurements found",
            }

        # Get user ID from Supabase
        user_response = client.get(
            f"{supabase_url}/rest/v1/users",
            headers=headers,
            params={"select": "id", "limit": "1"},
        )
        users = user_response.json()
        if not users:
            return {"success": False, "error": "No user found in database"}
        user_id = users[0]["id"]

        # Process and store measurements
        results = []

        for group in measure_groups:
            recorded_at = datetime.fromtimestamp(group["date"]).isoformat()

            weight = None
            fat_ratio = None
            muscle_mass = None

            for measure in group.get("measures", []):
                value = measure["value"] * (10 ** measure["unit"])

                if measure["type"] == MEASURE_TYPES["WEIGHT"]:
                    weight = round(value, 1)
                elif measure["type"] == MEASURE_TYPES["FAT_RATIO"]:
                    fat_ratio = round(value, 1)
                elif measure["type"] == MEASURE_TYPES["MUSCLE_MASS"]:
                    muscle_mass = round(value, 1)

            if weight:
                notes = None
                if fat_ratio:
                    notes = f"Fat: {fat_ratio}%"
                    if muscle_mass:
                        notes += f", Muscle: {muscle_mass}kg"

                # Check if entry exists
                existing = client.get(
                    f"{supabase_url}/rest/v1/metrics",
                    headers=headers,
                    params={
                        "user_id": f"eq.{user_id}",
                        "recorded_at": f"eq.{recorded_at}",
                        "select": "id",
                    },
                ).json()

                if existing:
                    # Update existing
                    client.patch(
                        f"{supabase_url}/rest/v1/metrics",
                        headers=headers,
                        params={"id": f"eq.{existing[0]['id']}"},
                        json={"weight": weight, "notes": notes},
                    )
                    results.append(
                        {
                            "action": "updated",
                            "recorded_at": recorded_at,
                            "weight": weight,
                        }
                    )
                else:
                    # Insert new
                    client.post(
                        f"{supabase_url}/rest/v1/metrics",
                        headers=headers,
                        json={
                            "user_id": user_id,
                            "recorded_at": recorded_at,
                            "timezone": "Asia/Tokyo",
                            "weight": weight,
                            "notes": notes,
                        },
                    )
                    results.append(
                        {
                            "action": "inserted",
                            "recorded_at": recorded_at,
                            "weight": weight,
                        }
                    )

        return {
            "success": True,
            "synced": len(results),
            "results": results,
            "message": _format_sync_message(results),
        }


def _format_sync_message(results: list[dict]) -> str:
    """Format sync results into a human-readable message."""
    if not results:
        return "No new weight measurements to sync"

    latest = results[0]
    weight_kg = latest.get("weight", 0)
    weight_lbs = weight_kg * 2.20462
    date = latest.get("recorded_at", "unknown")[:10]

    return f"Synced {len(results)} measurement(s). Latest: {weight_kg:.1f} kg ({weight_lbs:.1f} lbs) on {date}"
