#!/usr/bin/env python3
"""Refresh Whoop OAuth tokens before they expire.

Run this periodically (e.g., every 30 minutes via cron/systemd timer) to keep tokens fresh.
Whoop access tokens expire in 1 hour, and refresh tokens may rotate on each use.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

# Paths
TOKEN_FILE = Path.home() / ".config" / "jarvis" / "whoop_tokens.json"
ENV_FILE = Path.home() / "life_os" / ".env"

# Whoop OAuth endpoint
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"


def load_config() -> dict:
    """Load Whoop config from .env file."""
    config = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("WHOOP_") and "=" in line:
                key, value = line.split("=", 1)
                config[key] = value.strip()
    return config


def load_tokens() -> dict | None:
    """Load current tokens from file."""
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text())
        except Exception:
            pass
    return None


def save_tokens(tokens: dict) -> None:
    """Save tokens to file."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    tokens["refreshed_at"] = datetime.now().isoformat()
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    print(f"[{datetime.now()}] Tokens saved to {TOKEN_FILE}")


def refresh_tokens(client_id: str, client_secret: str, refresh_token: str) -> dict | None:
    """Refresh OAuth tokens."""
    try:
        response = httpx.post(
            WHOOP_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"[{datetime.now()}] Token refresh failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"[{datetime.now()}] Token refresh error: {e}")
        return None


def main():
    print(f"[{datetime.now()}] Starting Whoop token refresh...")

    # Load config
    config = load_config()
    client_id = config.get("WHOOP_CLIENT_ID")
    client_secret = config.get("WHOOP_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: WHOOP_CLIENT_ID or WHOOP_CLIENT_SECRET not found in .env")
        sys.exit(1)

    # Load current tokens (prefer saved file, fallback to .env)
    tokens = load_tokens()
    if tokens and tokens.get("refresh_token"):
        refresh_token = tokens["refresh_token"]
        print(f"Using refresh token from {TOKEN_FILE}")
    else:
        refresh_token = config.get("WHOOP_REFRESH_TOKEN")
        print("Using refresh token from .env")

    if not refresh_token:
        print("Error: No refresh token found")
        sys.exit(1)

    # Refresh tokens
    new_tokens = refresh_tokens(client_id, client_secret, refresh_token)

    if new_tokens:
        save_tokens(new_tokens)
        print(f"[{datetime.now()}] Token refresh successful!")
        print(f"  Access token expires in: {new_tokens.get('expires_in', 'unknown')} seconds")
        return 0
    else:
        print(f"[{datetime.now()}] Token refresh FAILED - manual re-auth may be needed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
