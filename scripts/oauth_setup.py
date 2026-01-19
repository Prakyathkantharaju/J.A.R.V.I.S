#!/usr/bin/env python3
"""OAuth setup helper for JARVIS services."""

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.config.settings import settings

app = typer.Typer(help="JARVIS OAuth Setup Helper")
console = Console()


@app.command()
def google():
    """Set up Google Calendar OAuth."""
    console.print(Panel("Google Calendar OAuth Setup", style="blue"))

    credentials_file = settings.google.credentials_file.expanduser()
    token_file = settings.google.token_file.expanduser()

    if not credentials_file.exists():
        console.print(
            "[yellow]Google credentials file not found.[/yellow]\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a project or select existing\n"
            "3. Enable Google Calendar API\n"
            "4. Create OAuth 2.0 credentials (Desktop app)\n"
            "5. Download credentials.json\n"
            f"6. Save to: {credentials_file}"
        )
        return

    console.print(f"[green]✓ Credentials file found: {credentials_file}[/green]")

    # Import and run OAuth flow
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                console.print("[yellow]Refreshing token...[/yellow]")
                creds.refresh(Request())
            else:
                console.print("[yellow]Starting OAuth flow...[/yellow]")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_file), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token
            token_file.parent.mkdir(parents=True, exist_ok=True)
            token_file.write_text(creds.to_json())
            console.print(f"[green]✓ Token saved to: {token_file}[/green]")
        else:
            console.print("[green]✓ Google Calendar already authenticated[/green]")

    except ImportError:
        console.print(
            "[red]Google libraries not installed.[/red]\n"
            "Run: uv add google-api-python-client google-auth-oauthlib"
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def whoop():
    """Set up Whoop OAuth."""
    console.print(Panel("Whoop OAuth Setup", style="blue"))

    client_id = settings.whoop.client_id
    client_secret = settings.whoop.client_secret.get_secret_value()

    if not client_id or not client_secret:
        console.print(
            "[yellow]Whoop credentials not configured.[/yellow]\n"
            "1. Go to https://developer.whoop.com/\n"
            "2. Create an application\n"
            "3. Note the Client ID and Client Secret\n"
            "4. Add to .env:\n"
            "   WHOOP_CLIENT_ID=your_client_id\n"
            "   WHOOP_CLIENT_SECRET=your_client_secret"
        )
        return

    console.print("[green]✓ Whoop credentials found[/green]")

    try:
        from whoopy import WhoopClient

        console.print("[yellow]Starting Whoop OAuth flow...[/yellow]")
        console.print(
            f"Redirect URI: {settings.whoop.redirect_uri}\n"
            "Make sure this matches your Whoop app settings."
        )

        # This will open browser for OAuth
        client = WhoopClient.authorize(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=settings.whoop.redirect_uri,
        )

        # Get tokens
        access_token = client.token.get("access_token")
        refresh_token = client.token.get("refresh_token")

        console.print("\n[green]✓ Whoop authenticated![/green]")
        console.print("\nAdd these to your .env file:")
        console.print(f"WHOOP_ACCESS_TOKEN={access_token}")
        console.print(f"WHOOP_REFRESH_TOKEN={refresh_token}")

    except ImportError:
        console.print(
            "[red]whoopy not installed.[/red]\n" "Run: uv sync --extra whoop"
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def microsoft():
    """Set up Microsoft/Outlook OAuth."""
    console.print(Panel("Microsoft Graph OAuth Setup", style="blue"))

    client_id = settings.microsoft.client_id
    client_secret = settings.microsoft.client_secret.get_secret_value()
    tenant_id = settings.microsoft.tenant_id

    if not client_id or not client_secret:
        console.print(
            "[yellow]Microsoft credentials not configured.[/yellow]\n"
            "1. Go to https://portal.azure.com/\n"
            "2. Register an application in Azure AD\n"
            "3. Add Calendar.Read and User.Read permissions\n"
            "4. Create a client secret\n"
            "5. Add to .env:\n"
            "   MICROSOFT_CLIENT_ID=your_client_id\n"
            "   MICROSOFT_CLIENT_SECRET=your_secret\n"
            "   MICROSOFT_TENANT_ID=your_tenant_id (or 'common')"
        )
        return

    console.print("[green]✓ Microsoft credentials found[/green]")

    try:
        import msal

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )

        # For app-only flow (daemon)
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )

        if "access_token" in result:
            console.print("[green]✓ Microsoft Graph authenticated![/green]")
            console.print(
                "[yellow]Note: Using app-only auth. For delegated access, "
                "additional setup required.[/yellow]"
            )
        else:
            console.print(f"[red]Error: {result.get('error_description')}[/red]")

    except ImportError:
        console.print("[red]MSAL not installed.[/red]\n" "Run: uv add msal")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def garmin():
    """Test Garmin Connect authentication."""
    console.print(Panel("Garmin Connect Setup", style="blue"))

    email = settings.garmin.email
    password = settings.garmin.password.get_secret_value()

    if not email or not password:
        console.print(
            "[yellow]Garmin credentials not configured.[/yellow]\n"
            "Add to .env:\n"
            "   GARMIN_EMAIL=your_email\n"
            "   GARMIN_PASSWORD=your_password"
        )
        return

    console.print("[green]✓ Garmin credentials found[/green]")

    try:
        from garminconnect import Garmin

        console.print("[yellow]Testing Garmin Connect login...[/yellow]")
        client = Garmin(email, password)
        client.login()

        name = client.get_full_name()
        console.print(f"[green]✓ Logged in as: {name}[/green]")

    except ImportError:
        console.print(
            "[red]garminconnect not installed.[/red]\n" "Run: uv add garminconnect"
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def home_assistant():
    """Test Home Assistant connection."""
    console.print(Panel("Home Assistant Setup", style="blue"))

    url = settings.home_assistant.url
    token = settings.home_assistant.token.get_secret_value()

    if not url or not token:
        console.print(
            "[yellow]Home Assistant not configured.[/yellow]\n"
            "1. In HA, go to Profile → Long-Lived Access Tokens\n"
            "2. Create a new token\n"
            "3. Add to .env:\n"
            "   HOME_ASSISTANT_URL=http://homeassistant.local:8123\n"
            "   HOME_ASSISTANT_TOKEN=your_token"
        )
        return

    console.print(f"[green]✓ Home Assistant URL: {url}[/green]")

    try:
        from homeassistant_api import Client

        console.print("[yellow]Testing Home Assistant connection...[/yellow]")
        client = Client(url, token)
        config = client.get_config()

        console.print(f"[green]✓ Connected to: {config.get('location_name')}[/green]")
        console.print(f"   Version: {config.get('version')}")

    except ImportError:
        console.print(
            "[red]homeassistant-api not installed.[/red]\n"
            "Run: uv add homeassistant-api"
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def all():
    """Run all OAuth setups."""
    console.print(Panel("JARVIS - Complete OAuth Setup", style="bold blue"))

    google()
    console.print()
    garmin()
    console.print()
    home_assistant()
    console.print()

    console.print(
        "\n[yellow]For Whoop and Microsoft, run individually:[/yellow]\n"
        "  uv run python scripts/oauth_setup.py whoop\n"
        "  uv run python scripts/oauth_setup.py microsoft"
    )


@app.command()
def status():
    """Check status of all service connections."""
    console.print(Panel("JARVIS - Connection Status", style="blue"))

    # Check each service
    checks = [
        ("Garmin", bool(settings.garmin.email)),
        ("Whoop", bool(settings.whoop.access_token.get_secret_value())),
        ("Google Calendar", settings.google.token_file.expanduser().exists()),
        ("Microsoft/Outlook", bool(settings.microsoft.client_id)),
        ("Obsidian", settings.obsidian.vault_path.expanduser().exists()),
        ("Home Assistant", bool(settings.home_assistant.token.get_secret_value())),
    ]

    for name, configured in checks:
        status = "[green]✓ Configured[/green]" if configured else "[red]✗ Not configured[/red]"
        console.print(f"  {name}: {status}")


if __name__ == "__main__":
    app()
