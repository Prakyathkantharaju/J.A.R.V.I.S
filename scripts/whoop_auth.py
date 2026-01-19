#!/usr/bin/env python3
"""Whoop OAuth setup script.

Run this locally to authenticate with Whoop and get tokens.

Usage:
    uv run python scripts/whoop_auth.py
"""

import os
import sys

try:
    from whoopy import WhoopClient
except ImportError:
    print("Error: whoopy library not installed.")
    print("Run: uv sync --extra whoop")
    sys.exit(1)

from jarvis.config.settings import settings


def main():
    client_id = settings.whoop.client_id
    client_secret = settings.whoop.client_secret.get_secret_value()
    redirect_uri = settings.whoop.redirect_uri

    if not client_id or not client_secret:
        print("Error: Whoop credentials not configured in .env")
        print()
        print("Add these to your .env file:")
        print("  WHOOP_CLIENT_ID=your_client_id")
        print("  WHOOP_CLIENT_SECRET=your_client_secret")
        print("  WHOOP_REDIRECT_URI=http://localhost:8080/callback")
        print()
        print("Get credentials from: https://developer.whoop.com")
        sys.exit(1)

    print("Starting Whoop OAuth flow...")
    print(f"Client ID: {client_id[:8]}...")
    print(f"Redirect URI: {redirect_uri}")
    print()
    print("A browser window will open. Log in to Whoop and authorize the app.")
    print()

    try:
        client = WhoopClient.auth_flow(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

        # Get token info from the client
        token_info = client._client.token_info
        access_token = token_info.access_token
        refresh_token = token_info.refresh_token

        print()
        print("=" * 60)
        print("SUCCESS! Add these to your .env file:")
        print("=" * 60)
        print()
        print(f"WHOOP_ACCESS_TOKEN={access_token}")
        print(f"WHOOP_REFRESH_TOKEN={refresh_token}")
        print()
        print("Then sync to Pi:")
        print("  scp .env pi@10.0.0.7:~/jarvis/.env")

    except Exception as e:
        print(f"Error during OAuth: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
