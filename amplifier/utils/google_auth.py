"""Google OAuth2 authentication for Gmail and Calendar APIs.

This module handles the OAuth2 flow for Google APIs:
- Loads client credentials from ~/.googleauth/credentials.json
- Stores/refreshes tokens per-app in ~/.googleauth/{app_name}/
- Opens browser for initial authorization when needed
- Automatically refreshes expired tokens

Usage:
    from amplifier.utils.google_auth import get_google_credentials, GoogleScopes

    # Get credentials for Gmail
    creds = get_google_credentials(
        app_name="amplifier",
        scopes=[GoogleScopes.GMAIL_MODIFY, GoogleScopes.GMAIL_SEND]
    )

    # Use with Google API client
    from googleapiclient.discovery import build
    service = build('gmail', 'v1', credentials=creds)
"""

from __future__ import annotations

import json
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx

if TYPE_CHECKING:
    pass

# Default paths
GOOGLE_AUTH_DIR = Path.home() / ".googleauth"
CREDENTIALS_FILE = GOOGLE_AUTH_DIR / "credentials.json"


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
            return False
        # Add 5 minute buffer
        return datetime.now(timezone.utc) >= self.expiry.replace(
            tzinfo=timezone.utc
        )

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

    @classmethod
    def from_dict(cls, data: dict) -> "GoogleCredentials":
        """Create from dict."""
        expiry = None
        if data.get("expiry"):
            try:
                expiry = datetime.fromisoformat(data["expiry"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        elif data.get("expiry_date"):
            # Handle legacy format (milliseconds since epoch)
            try:
                expiry = datetime.fromtimestamp(
                    data["expiry_date"] / 1000, tz=timezone.utc
                )
            except (ValueError, TypeError):
                pass

        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            scopes=data.get("scopes", []) or data.get("scope", "").split(),
            expiry=expiry,
        )


def _load_client_config(credentials_file: Path = CREDENTIALS_FILE) -> dict:
    """Load OAuth client configuration from credentials.json."""
    if not credentials_file.exists():
        raise FileNotFoundError(
            f"Google credentials not found at {credentials_file}\n"
            "Download from: https://console.cloud.google.com/apis/credentials"
        )

    data = json.loads(credentials_file.read_text())

    # Handle "installed" (desktop) or "web" app types
    if "installed" in data:
        return data["installed"]
    elif "web" in data:
        return data["web"]
    else:
        raise ValueError(f"Invalid credentials.json format: {list(data.keys())}")


def _get_token_path(app_name: str, service: str) -> Path:
    """Get the token file path for an app/service combination."""
    token_dir = GOOGLE_AUTH_DIR / app_name
    token_dir.mkdir(parents=True, exist_ok=True)
    return token_dir / f"{service}_token.json"


def _load_token(token_path: Path) -> dict | None:
    """Load token from file if it exists."""
    if token_path.exists():
        try:
            return json.loads(token_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_token(token_path: Path, token_data: dict) -> None:
    """Save token to file."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(token_data, indent=2))
    # Secure the token file
    token_path.chmod(0o600)


def _refresh_access_token(creds: GoogleCredentials) -> GoogleCredentials:
    """Refresh the access token using the refresh token."""
    response = httpx.post(
        creds.token_uri,
        data={
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "refresh_token": creds.refresh_token,
            "grant_type": "refresh_token",
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {response.text}")

    data = response.json()

    return GoogleCredentials(
        access_token=data["access_token"],
        refresh_token=creds.refresh_token,  # Keep original refresh token
        token_uri=creds.token_uri,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        scopes=creds.scopes,
        expiry=datetime.now(timezone.utc)
        + __import__("datetime").timedelta(seconds=data.get("expires_in", 3600)),
    )


def _run_oauth_flow(
    client_config: dict,
    scopes: list[str],
    redirect_uri: str = "http://localhost:8085",
) -> dict:
    """Run the OAuth2 authorization flow.

    Opens browser for user authorization and runs a local server to capture the callback.
    """
    import socket
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    client_id = client_config["client_id"]
    client_secret = client_config["client_secret"]
    token_uri = client_config.get("token_uri", "https://oauth2.googleapis.com/token")
    auth_uri = client_config.get(
        "auth_uri", "https://accounts.google.com/o/oauth2/auth"
    )

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

    # Parse port from redirect_uri
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or 8085

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
            else:
                self.send_response(400)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress logging

    # Check if port is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("localhost", port))
        sock.close()
    except OSError:
        raise RuntimeError(
            f"Port {port} is in use. Close the application using it and try again."
        )

    # Start local server
    server = HTTPServer(("localhost", port), CallbackHandler)
    server.timeout = 120  # 2 minute timeout

    print(f"\n🔐 Opening browser for Google authorization...")
    print(f"   If browser doesn't open, visit:\n   {auth_url}\n")
    webbrowser.open(auth_url)

    print("⏳ Waiting for authorization (timeout: 2 minutes)...")

    # Handle one request
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
    token_data["client_id"] = client_id
    token_data["client_secret"] = client_secret
    token_data["token_uri"] = token_uri
    token_data["scopes"] = scopes

    print("✅ Authorization successful!")

    return token_data


def get_google_credentials(
    app_name: str = "amplifier",
    scopes: list[str] | None = None,
    service: str = "google",
    force_refresh: bool = False,
    credentials_file: Path = CREDENTIALS_FILE,
) -> GoogleCredentials:
    """Get Google OAuth2 credentials, refreshing or authorizing as needed.

    Args:
        app_name: Application name for token storage (e.g., "amplifier")
        scopes: Required OAuth scopes
        service: Service name for token file (e.g., "gmail", "calendar")
        force_refresh: Force token refresh even if not expired
        credentials_file: Path to credentials.json

    Returns:
        GoogleCredentials object ready to use with Google APIs

    Raises:
        FileNotFoundError: If credentials.json not found
        RuntimeError: If authorization fails
    """
    scopes = scopes or [GoogleScopes.GMAIL_READONLY]

    # Load client config
    client_config = _load_client_config(credentials_file)

    # Try to load existing token
    token_path = _get_token_path(app_name, service)
    token_data = _load_token(token_path)

    creds = None

    if token_data:
        # Merge client config into token data
        token_data["client_id"] = client_config["client_id"]
        token_data["client_secret"] = client_config["client_secret"]
        token_data["token_uri"] = client_config.get(
            "token_uri", "https://oauth2.googleapis.com/token"
        )

        creds = GoogleCredentials.from_dict(token_data)

        # Check if we have all required scopes
        existing_scopes = set(creds.scopes)
        required_scopes = set(scopes)

        if not required_scopes.issubset(existing_scopes):
            print(f"⚠️  Additional scopes required. Re-authorizing...")
            creds = None
        elif creds.expired or force_refresh:
            # Try to refresh
            try:
                creds = _refresh_access_token(creds)
                _save_token(token_path, creds.to_dict())
            except Exception as e:
                print(f"⚠️  Token refresh failed: {e}. Re-authorizing...")
                creds = None

    if creds is None:
        # Need to run OAuth flow
        token_data = _run_oauth_flow(client_config, scopes)
        creds = GoogleCredentials.from_dict(token_data)
        _save_token(token_path, creds.to_dict())

    return creds


def authorize_google(
    app_name: str = "amplifier",
    scopes: list[str] | None = None,
    service: str = "google",
) -> None:
    """Explicitly run authorization flow (useful for initial setup).

    Args:
        app_name: Application name for token storage
        scopes: OAuth scopes to request
        service: Service name for token file
    """
    scopes = scopes or [
        GoogleScopes.GMAIL_MODIFY,
        GoogleScopes.GMAIL_SEND,
        GoogleScopes.CALENDAR_EVENTS,
    ]

    print(f"🔐 Authorizing Google APIs for {app_name}...")
    print(f"   Scopes: {', '.join(s.split('/')[-1] for s in scopes)}")

    get_google_credentials(
        app_name=app_name,
        scopes=scopes,
        service=service,
        force_refresh=True,
    )

    print(f"\n✅ Credentials saved to ~/.googleauth/{app_name}/{service}_token.json")


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point for authorization."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Google OAuth2 Authorization")
    parser.add_argument(
        "--app",
        default="amplifier",
        help="Application name (default: amplifier)",
    )
    parser.add_argument(
        "--service",
        default="google",
        help="Service name (default: google)",
    )
    parser.add_argument(
        "--scopes",
        nargs="+",
        help="OAuth scopes (default: gmail.modify, gmail.send, calendar.events)",
    )
    parser.add_argument(
        "--gmail-only",
        action="store_true",
        help="Only authorize Gmail scopes",
    )
    parser.add_argument(
        "--calendar-only",
        action="store_true",
        help="Only authorize Calendar scopes",
    )

    args = parser.parse_args()

    if args.scopes:
        scopes = args.scopes
    elif args.gmail_only:
        scopes = [GoogleScopes.GMAIL_MODIFY, GoogleScopes.GMAIL_SEND]
    elif args.calendar_only:
        scopes = [GoogleScopes.CALENDAR_EVENTS]
    else:
        scopes = [
            GoogleScopes.GMAIL_MODIFY,
            GoogleScopes.GMAIL_SEND,
            GoogleScopes.CALENDAR_EVENTS,
        ]

    try:
        authorize_google(app_name=args.app, scopes=scopes, service=args.service)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
