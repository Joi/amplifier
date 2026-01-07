"""Google OAuth2 authentication for Gmail and Calendar APIs.

This module handles OAuth2 for Google APIs using age-encrypted secrets:
- Client credentials from GOOGLE_CLIENT_ID/SECRET in age secrets
- Refresh token from GOOGLE_REFRESH_TOKEN in age secrets
- Access tokens cached in ~/.cache/amplifier/google/ (short-lived)

For initial authorization (one-time browser flow):
    python -m amplifier.utils.google_auth

After that, tokens are refreshed automatically without browser.

Usage:
    from amplifier.utils.google_auth import get_google_credentials, GoogleScopes

    # Get credentials for Gmail
    creds = get_google_credentials(
        scopes=[GoogleScopes.GMAIL_MODIFY, GoogleScopes.GMAIL_SEND]
    )

    # Use with httpx
    headers = {"Authorization": f"Bearer {creds.access_token}"}
"""

from __future__ import annotations

import json
import os
import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx

if TYPE_CHECKING:
    pass

# Paths
AGE_KEY_PATH = Path.home() / ".config" / "age" / "secrets.key"
AGE_SECRETS_PATH = Path.home() / "dotfiles-private" / "amplifier-secrets.env.age"
ACCESS_TOKEN_CACHE = Path.home() / ".cache" / "amplifier" / "google"
HYDRATED_DIR = Path.home() / ".cache" / "amplifier" / "google-hydrated"

# Legacy path for fallback
LEGACY_CREDENTIALS_FILE = Path.home() / ".googleauth" / "credentials.json"


class GoogleScopes:
    """Common Google API scopes."""

    # Gmail
    GMAIL_READONLY = "https://www.googleapis.com/auth/gmail.readonly"
    GMAIL_MODIFY = "https://www.googleapis.com/auth/gmail.modify"
    GMAIL_SEND = "https://www.googleapis.com/auth/gmail.send"
    GMAIL_COMPOSE = "https://www.googleapis.com/auth/gmail.compose"

    # Calendar
    CALENDAR_READONLY = "https://www.googleapis.com/auth/calendar.readonly"
    CALENDAR_EVENTS = "https://www.googleapis.com/auth/calendar.events"
    CALENDAR_FULL = "https://www.googleapis.com/auth/calendar"

    # Sheets
    SHEETS_READONLY = "https://www.googleapis.com/auth/spreadsheets.readonly"
    SHEETS = "https://www.googleapis.com/auth/spreadsheets"


@dataclass
class GoogleCredentials:
    """OAuth2 credentials for Google APIs."""

    access_token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
    expiry: datetime | None = None

    @property
    def expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expiry is None:
            return True  # Assume expired if no expiry
        # Add 5 minute buffer
        return datetime.now(timezone.utc) >= self.expiry - timedelta(minutes=5)

    @property
    def valid(self) -> bool:
        """Check if credentials are valid (have token and not expired)."""
        return bool(self.access_token) and not self.expired

    def to_dict(self) -> dict:
        """Convert to dict for saving."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_uri": self.token_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scopes": self.scopes,
            "expiry": self.expiry.isoformat() if self.expiry else None,
        }


def _load_age_secrets() -> dict[str, str]:
    """Load secrets from age-encrypted file."""
    if not AGE_KEY_PATH.exists():
        raise FileNotFoundError(f"Age key not found at {AGE_KEY_PATH}")
    if not AGE_SECRETS_PATH.exists():
        raise FileNotFoundError(f"Age secrets not found at {AGE_SECRETS_PATH}")

    result = subprocess.run(
        ["age", "-d", "-i", str(AGE_KEY_PATH), str(AGE_SECRETS_PATH)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to decrypt secrets: {result.stderr}")

    secrets = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            secrets[key.strip()] = value.strip()

    return secrets


def _get_google_secrets() -> tuple[str, str, str]:
    """Get Google OAuth credentials from age secrets.
    
    Returns:
        Tuple of (client_id, client_secret, refresh_token)
    """
    secrets = _load_age_secrets()

    client_id = secrets.get("GOOGLE_CLIENT_ID")
    client_secret = secrets.get("GOOGLE_CLIENT_SECRET")
    refresh_token = secrets.get("GOOGLE_REFRESH_TOKEN")

    if not client_id or not client_secret:
        raise ValueError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not found in secrets.\n"
            "Add them to ~/dotfiles-private/amplifier-secrets.env.age"
        )

    if not refresh_token:
        raise ValueError(
            "GOOGLE_REFRESH_TOKEN not found in secrets.\n"
            "Run: python -m amplifier.utils.google_auth --initial-auth\n"
            "to authorize and get a refresh token."
        )

    return client_id, client_secret, refresh_token


def _load_cached_access_token() -> dict | None:
    """Load cached access token if it exists and is valid."""
    cache_file = ACCESS_TOKEN_CACHE / "access_token.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text())
        expiry_str = data.get("expiry")
        if expiry_str:
            expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) < expiry - timedelta(minutes=5):
                return data
    except (json.JSONDecodeError, OSError, ValueError):
        pass

    return None


def _save_cached_access_token(access_token: str, expires_in: int, scopes: list[str]) -> None:
    """Cache access token with expiry."""
    ACCESS_TOKEN_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = ACCESS_TOKEN_CACHE / "access_token.json"

    data = {
        "access_token": access_token,
        "scopes": scopes,
        "expiry": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
    }

    cache_file.write_text(json.dumps(data, indent=2))
    cache_file.chmod(0o600)


def _refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> tuple[str, int]:
    """Refresh the access token using the refresh token.
    
    Returns:
        Tuple of (access_token, expires_in_seconds)
    """
    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {response.text}")

    data = response.json()
    return data["access_token"], data.get("expires_in", 3600)


def get_google_credentials(
    scopes: list[str] | None = None,
    force_refresh: bool = False,
    # Legacy parameters (ignored but kept for compatibility)
    app_name: str = "amplifier",
    service: str = "google",
) -> GoogleCredentials:
    """Get Google OAuth2 credentials from age-encrypted secrets.

    Args:
        scopes: Required OAuth scopes (for documentation, actual scopes in token)
        force_refresh: Force token refresh even if cached token is valid

    Returns:
        GoogleCredentials object ready to use with Google APIs

    Raises:
        ValueError: If secrets not configured
        RuntimeError: If token refresh fails
    """
    scopes = scopes or [GoogleScopes.GMAIL_READONLY]

    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = _load_cached_access_token()
        if cached:
            client_id, client_secret, refresh_token = _get_google_secrets()
            return GoogleCredentials(
                access_token=cached["access_token"],
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=cached.get("scopes", scopes),
                expiry=datetime.fromisoformat(cached["expiry"].replace("Z", "+00:00")),
            )

    # Load secrets and refresh
    client_id, client_secret, refresh_token = _get_google_secrets()

    access_token, expires_in = _refresh_access_token(
        client_id, client_secret, refresh_token
    )

    # Cache the new access token
    _save_cached_access_token(access_token, expires_in, scopes)

    return GoogleCredentials(
        access_token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    )


def hydrate_google_tokens(
    output_dir: Path | None = None,
    include_credentials_json: bool = True,
) -> dict[str, Path]:
    """Write Google tokens to plain files for tools that need them.
    
    This creates:
    - credentials.json (OAuth client config)
    - token.json (with refresh token and cached access token)
    
    These files are written to a cache directory and should NOT be
    committed to version control.
    
    Args:
        output_dir: Directory to write files (default: ~/.cache/amplifier/google-hydrated/)
        include_credentials_json: Also write credentials.json
    
    Returns:
        Dict mapping file type to path: {"credentials": Path, "token": Path}
    """
    output_dir = output_dir or HYDRATED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    client_id, client_secret, refresh_token = _get_google_secrets()

    paths = {}

    # Write credentials.json (OAuth client config)
    if include_credentials_json:
        creds_path = output_dir / "credentials.json"
        creds_data = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8085"],
            }
        }
        creds_path.write_text(json.dumps(creds_data, indent=2))
        creds_path.chmod(0o600)
        paths["credentials"] = creds_path

    # Get current access token (refresh if needed)
    try:
        cached = _load_cached_access_token()
        if cached:
            access_token = cached["access_token"]
            expiry = cached["expiry"]
        else:
            access_token, expires_in = _refresh_access_token(
                client_id, client_secret, refresh_token
            )
            expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
            _save_cached_access_token(access_token, expires_in, [])
    except Exception:
        access_token = ""
        expiry = None

    # Write token.json (for obs-dailynotes and similar tools)
    token_path = output_dir / "token.json"
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": [
            GoogleScopes.GMAIL_READONLY,
            GoogleScopes.GMAIL_MODIFY,
            GoogleScopes.GMAIL_SEND,
            GoogleScopes.CALENDAR_READONLY,
            GoogleScopes.CALENDAR_EVENTS,
        ],
    }
    if expiry:
        token_data["expiry"] = expiry

    token_path.write_text(json.dumps(token_data, indent=2))
    token_path.chmod(0o600)
    paths["token"] = token_path

    return paths


def hydrate_for_obs_dailynotes() -> dict[str, Path]:
    """Hydrate tokens specifically for obs-dailynotes.
    
    Creates files at ~/.cache/amplifier/google-hydrated/ that can be
    referenced by obs-dailynotes via environment variables.
    
    Returns:
        Dict with paths to credentials.json and token.json
    """
    paths = hydrate_google_tokens()
    
    # Also create separate calendar and gmail token files
    # (obs-dailynotes uses separate files)
    client_id, client_secret, refresh_token = _get_google_secrets()
    
    # Get current access token
    cached = _load_cached_access_token()
    access_token = cached["access_token"] if cached else ""
    
    for service in ["calendar", "gmail"]:
        token_path = HYDRATED_DIR / f"{service}_token.json"
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        token_path.write_text(json.dumps(token_data, indent=2))
        token_path.chmod(0o600)
        paths[service] = token_path
    
    return paths


# =============================================================================
# Initial Authorization (One-time browser flow)
# =============================================================================


def _run_initial_oauth_flow(
    client_id: str,
    client_secret: str,
    scopes: list[str],
) -> str:
    """Run the OAuth2 authorization flow to get a refresh token.
    
    This is only needed once. After getting the refresh token,
    add it to your age-encrypted secrets file.
    
    Returns:
        The refresh token
    """
    import socket
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    redirect_uri = "http://localhost:8085"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"

    # Build authorization URL
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",  # Force consent to get refresh token
    }
    auth_url = f"{auth_uri}?{urlencode(auth_params)}"

    # Storage for the authorization code
    auth_code = {"code": None, "error": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)

            if "code" in params:
                auth_code["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h1>Authorization successful!</h1>"
                    b"<p>You can close this window.</p></body></html>"
                )
            elif "error" in params:
                auth_code["error"] = params.get("error_description", params["error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h1>Authorization failed</h1>"
                    f"<p>{auth_code['error']}</p></body></html>".encode()
                )

        def log_message(self, format, *args):
            pass  # Suppress logging

    # Check if port is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("localhost", 8085))
        sock.close()
    except OSError:
        raise RuntimeError(
            "Port 8085 is in use. Close the application using it and try again."
        )

    # Start local server
    server = HTTPServer(("localhost", 8085), CallbackHandler)
    server.timeout = 120

    print(f"\n🔐 Opening browser for Google authorization...")
    print(f"   If browser doesn't open, visit:\n   {auth_url}\n")
    webbrowser.open(auth_url)

    print("⏳ Waiting for authorization (timeout: 2 minutes)...")

    server.handle_request()
    server.server_close()

    if auth_code["error"]:
        raise RuntimeError(f"Authorization failed: {auth_code['error']}")

    if not auth_code["code"]:
        raise RuntimeError("No authorization code received")

    # Exchange code for tokens
    print("🔄 Exchanging code for tokens...")

    response = httpx.post(
        token_uri,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code["code"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"Token exchange failed: {response.text}")

    token_data = response.json()
    refresh_token = token_data.get("refresh_token")

    if not refresh_token:
        raise RuntimeError("No refresh token received. Try again with prompt=consent.")

    return refresh_token


def authorize_google(
    scopes: list[str] | None = None,
    # Legacy parameters (ignored)
    app_name: str = "amplifier",
    service: str = "google",
) -> None:
    """Run initial authorization to get a refresh token.
    
    This opens a browser for Google sign-in. After authorization,
    it prints the refresh token to add to your age secrets.
    """
    scopes = scopes or [
        GoogleScopes.GMAIL_READONLY,
        GoogleScopes.GMAIL_MODIFY,
        GoogleScopes.GMAIL_SEND,
        GoogleScopes.CALENDAR_READONLY,
        GoogleScopes.CALENDAR_EVENTS,
    ]

    print("🔐 Google OAuth2 Initial Authorization")
    print(f"   Scopes: {', '.join(s.split('/')[-1] for s in scopes)}")

    # Try to get client_id/secret from age secrets
    try:
        secrets = _load_age_secrets()
        client_id = secrets.get("GOOGLE_CLIENT_ID")
        client_secret = secrets.get("GOOGLE_CLIENT_SECRET")
    except Exception:
        client_id = None
        client_secret = None

    # Fall back to credentials.json if not in age secrets
    if not client_id or not client_secret:
        if LEGACY_CREDENTIALS_FILE.exists():
            print(f"   Loading client config from {LEGACY_CREDENTIALS_FILE}")
            data = json.loads(LEGACY_CREDENTIALS_FILE.read_text())
            config = data.get("installed") or data.get("web", {})
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")
        else:
            raise ValueError(
                "No Google client credentials found.\n"
                "Either add GOOGLE_CLIENT_ID/SECRET to age secrets,\n"
                "or place credentials.json at ~/.googleauth/credentials.json"
            )

    refresh_token = _run_initial_oauth_flow(client_id, client_secret, scopes)

    print("\n" + "=" * 60)
    print("✅ Authorization successful!")
    print("=" * 60)
    print("\nAdd this to your age-encrypted secrets file:")
    print(f"\nGOOGLE_REFRESH_TOKEN={refresh_token}")
    print("\nTo update secrets:")
    print("  1. Decrypt: age -d -i ~/.config/age/secrets.key ~/dotfiles-private/amplifier-secrets.env.age > /tmp/secrets.env")
    print("  2. Add the GOOGLE_REFRESH_TOKEN line")
    print("  3. Re-encrypt: age -r <your-public-key> -o ~/dotfiles-private/amplifier-secrets.env.age /tmp/secrets.env")
    print("  4. Delete temp: rm /tmp/secrets.env")


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Google OAuth2 Authentication")
    parser.add_argument(
        "--initial-auth",
        action="store_true",
        help="Run initial authorization flow (opens browser)",
    )
    parser.add_argument(
        "--hydrate",
        action="store_true",
        help="Write plain token files for tools that need them",
    )
    parser.add_argument(
        "--hydrate-obs",
        action="store_true",
        help="Hydrate tokens for obs-dailynotes",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test credentials by fetching user info",
    )
    parser.add_argument(
        "--show-token",
        action="store_true",
        help="Show current access token (for debugging)",
    )

    args = parser.parse_args()

    try:
        if args.initial_auth:
            authorize_google()

        elif args.hydrate:
            paths = hydrate_google_tokens()
            print("✅ Hydrated Google tokens:")
            for name, path in paths.items():
                print(f"   {name}: {path}")

        elif args.hydrate_obs:
            paths = hydrate_for_obs_dailynotes()
            print("✅ Hydrated tokens for obs-dailynotes:")
            for name, path in paths.items():
                print(f"   {name}: {path}")
            print("\nUpdate obs-dailynotes.env:")
            print(f"   GCAL_CREDS_PATH={paths['credentials']}")
            print(f"   GCAL_TOKEN_PATH={paths['calendar']}")
            print(f"   GMAIL_CREDS_PATH={paths['credentials']}")
            print(f"   GMAIL_TOKEN_PATH={paths['gmail']}")

        elif args.test:
            creds = get_google_credentials()
            print("✅ Credentials valid!")
            print(f"   Access token: {creds.access_token[:20]}...")
            print(f"   Expiry: {creds.expiry}")

            # Test with Gmail API
            response = httpx.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {creds.access_token}"},
            )
            if response.status_code == 200:
                profile = response.json()
                print(f"   Email: {profile.get('emailAddress')}")
            else:
                print(f"   Gmail API test failed: {response.status_code}")

        elif args.show_token:
            creds = get_google_credentials()
            print(creds.access_token)

        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
