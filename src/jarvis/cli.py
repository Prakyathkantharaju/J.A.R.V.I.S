"""JARVIS Command Line Interface."""

import asyncio
from datetime import date

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="jarvis",
    help="JARVIS - Personal AI Assistant",
    no_args_is_help=True,
)
console = Console()


@app.command()
def status():
    """Show JARVIS status and connection health."""
    console.print(Panel("JARVIS Status", style="blue"))

    async def check_status():
        from jarvis.adapters import (
            GarminAdapter,
            GoogleCalendarAdapter,
            HomeAssistantAdapter,
            ObsidianAdapter,
            OutlookAdapter,
            WhoopAdapter,
        )

        adapters = [
            ("Garmin", GarminAdapter()),
            ("Whoop", WhoopAdapter()),
            ("Google Calendar", GoogleCalendarAdapter()),
            ("Outlook", OutlookAdapter()),
            ("Obsidian", ObsidianAdapter()),
            ("Home Assistant", HomeAssistantAdapter()),
        ]

        table = Table(title="Adapter Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")

        for name, adapter in adapters:
            try:
                connected = await adapter.connect()
                status = "✓ Connected" if connected else "✗ Not configured"
                await adapter.disconnect()
            except Exception as e:
                status = f"✗ Error: {str(e)[:30]}"

            table.add_row(name, status)

        console.print(table)

    asyncio.run(check_status())


@app.command()
def briefing():
    """Get morning briefing."""
    console.print(Panel("Morning Briefing", style="blue"))

    async def get_briefing():
        from jarvis.aggregators.daily import get_daily_briefing

        data = await get_daily_briefing()
        console.print(f"\n[bold]{data.get('summary', 'No summary available')}[/bold]\n")

        # Show details
        sections = data.get("sections", {})

        if "health" in sections:
            health = sections["health"]
            console.print("[cyan]Health:[/cyan]")
            if "sleep" in health:
                sleep = health["sleep"]
                console.print(f"  Sleep: {sleep.get('total_hours', 'N/A'):.1f} hours")
            if "recovery" in health:
                recovery = health["recovery"]
                console.print(f"  Recovery: {recovery.get('score', 'N/A')}%")

        if "calendar" in sections:
            calendar = sections["calendar"]
            events = calendar.get("events", [])
            console.print(f"\n[cyan]Calendar:[/cyan] {len(events)} events today")
            for event in events[:5]:
                console.print(f"  • {event.get('title')} @ {event.get('start', '')[:16]}")

    asyncio.run(get_briefing())


@app.command()
def health(
    days: int = typer.Option(1, help="Number of days to show"),
):
    """Show health data from Whoop and Garmin."""
    console.print(Panel("Health Summary", style="blue"))

    async def show_health():
        from jarvis.aggregators.health import get_health_summary

        data = await get_health_summary()

        # Sleep
        sleep = data.get("sleep", {})
        if sleep:
            console.print("\n[cyan]Sleep:[/cyan]")
            console.print(f"  Total: {sleep.get('total_hours', 0):.1f} hours")
            if sleep.get("quality_score"):
                console.print(f"  Quality: {sleep['quality_score']}%")

        # Recovery
        recovery = data.get("recovery", {})
        if recovery:
            console.print("\n[cyan]Recovery:[/cyan]")
            if recovery.get("score"):
                console.print(f"  Score: {recovery['score']}%")
            if recovery.get("hrv_ms"):
                console.print(f"  HRV: {recovery['hrv_ms']} ms")

        # Activity
        activity = data.get("activity", {})
        if activity:
            console.print("\n[cyan]Activity:[/cyan]")
            if activity.get("steps"):
                console.print(f"  Steps: {activity['steps']:,}")
            if activity.get("calories"):
                console.print(f"  Calories: {activity['calories']:,}")

    asyncio.run(show_health())


@app.command()
def calendar(
    days: int = typer.Option(1, help="Number of days to show"),
):
    """Show merged calendar from Google and Outlook."""
    console.print(Panel("Calendar", style="blue"))

    async def show_calendar():
        from datetime import timedelta

        from jarvis.aggregators.calendar import get_merged_calendar

        today = date.today()
        end = today + timedelta(days=days - 1)

        data = await get_merged_calendar(today)
        events = data.get("events", [])

        if not events:
            console.print("[yellow]No events found[/yellow]")
            return

        table = Table(title=f"Events ({today} - {end})")
        table.add_column("Time", style="cyan")
        table.add_column("Event", style="white")
        table.add_column("Calendar", style="green")

        for event in events:
            start = event.get("start", "")[:16].replace("T", " ")
            title = event.get("title", "No title")[:40]
            cal_type = event.get("calendar_type", "unknown")
            table.add_row(start, title, cal_type)

        console.print(table)

    asyncio.run(show_calendar())


@app.command()
def notes(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, help="Max results"),
):
    """Search Obsidian notes."""
    console.print(Panel(f"Searching: {query}", style="blue"))

    async def search():
        from jarvis.adapters.obsidian import search_obsidian

        results = await search_obsidian(query)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        for result in results[:limit]:
            console.print(f"\n[cyan]{result['title']}[/cyan]")
            console.print(f"  Path: {result['path']}")
            for match in result.get("matches", []):
                console.print(f"  Line {match['line']}: {match['text'][:60]}...")

    asyncio.run(search())


@app.command()
def home(
    action: str = typer.Argument(..., help="Action: on, off, toggle, status"),
    entity: str = typer.Argument(..., help="Entity ID (e.g., light.living_room)"),
):
    """Control Home Assistant devices."""
    console.print(Panel(f"{action.upper()} {entity}", style="blue"))

    async def control():
        from jarvis.adapters.home_assistant import HomeAssistantAdapter

        async with HomeAssistantAdapter() as ha:
            if action == "on":
                result = await ha.turn_on(entity)
            elif action == "off":
                result = await ha.turn_off(entity)
            elif action == "toggle":
                result = await ha.toggle(entity)
            elif action == "status":
                data = await ha.fetch(date.today(), entity_ids=[entity])
                state = data.get("states", {}).get(entity, {})
                console.print(f"State: {state.get('state')}")
                console.print(f"Attributes: {state.get('attributes')}")
                return
            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                return

            if result:
                console.print(f"[green]✓ {entity} {action}[/green]")
            else:
                console.print(f"[red]✗ Failed to {action} {entity}[/red]")

    asyncio.run(control())


@app.command()
def speak(
    message: str = typer.Argument(..., help="Message to speak"),
    speaker: str = typer.Option(
        "media_player.living_room", help="Speaker entity ID"
    ),
):
    """Speak a message via Home Assistant TTS."""
    async def do_speak():
        from jarvis.adapters.home_assistant import speak_message

        result = await speak_message(message, speaker)
        if result:
            console.print(f"[green]✓ Speaking: {message}[/green]")
        else:
            console.print("[red]✗ Failed to speak[/red]")

    asyncio.run(do_speak())


@app.command()
def sync():
    """Manually trigger data sync from all sources."""
    console.print(Panel("Syncing Data", style="blue"))

    async def do_sync():
        from jarvis.adapters import (
            GarminAdapter,
            GoogleCalendarAdapter,
            ObsidianAdapter,
            WhoopAdapter,
        )

        adapters = [
            ("Garmin", GarminAdapter()),
            ("Whoop", WhoopAdapter()),
            ("Google Calendar", GoogleCalendarAdapter()),
            ("Obsidian", ObsidianAdapter()),
        ]

        for name, adapter in adapters:
            try:
                console.print(f"[yellow]Syncing {name}...[/yellow]")
                await adapter.connect()
                data = await adapter.fetch_today()
                await adapter.disconnect()
                console.print(f"[green]✓ {name} synced[/green]")
            except Exception as e:
                console.print(f"[red]✗ {name}: {e}[/red]")

    asyncio.run(do_sync())


@app.command()
def version():
    """Show JARVIS version."""
    from jarvis import __version__

    console.print(f"JARVIS v{__version__}")


if __name__ == "__main__":
    app()
