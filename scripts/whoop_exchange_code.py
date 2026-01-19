#!/usr/bin/env python3
"""Exchange Whoop authorization code for tokens.

Usage:
    uv run python scripts/whoop_exchange_code.py <authorization_code>
"""

import sys
import requests

from jarvis.config.settings import settings


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/whoop_exchange_code.py <authorization_code>")
        print()
        print("The authorization code is in the callback URL after 'code='")
        sys.exit(1)

    code = sys.argv[1]

    client_id = settings.whoop.client_id
    client_secret = settings.whoop.client_secret.get_secret_value()
    redirect_uri = settings.whoop.redirect_uri

    if not client_id or not client_secret:
        print("Error: Whoop credentials not configured in .env")
        sys.exit(1)

    print(f"Exchanging authorization code for tokens...")
    print(f"Client ID: {client_id[:8]}...")
    print(f"Redirect URI: {redirect_uri}")
    print()

    # Exchange code for tokens
    token_url = "https://api.prod.whoop.com/oauth/oauth2/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()

        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        print("=" * 60)
        print("SUCCESS! Add these to your .env file:")
        print("=" * 60)
        print()
        print(f"WHOOP_ACCESS_TOKEN={access_token}")
        print(f"WHOOP_REFRESH_TOKEN={refresh_token}")
        print()
        print("Then sync to Pi:")
        print("  scp .env pi@10.0.0.7:~/jarvis/.env")

    except requests.exceptions.HTTPError as e:
        print(f"Error exchanging code: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
