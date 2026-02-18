# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JARVIS is a personal AI operating system that aggregates data from health trackers (Whoop, Garmin), calendars (Google, Outlook), notes (Obsidian), and smart home (Home Assistant). It runs on Raspberry Pi hardware with WhatsApp integration via OpenClaw.

## Commands

```bash
# Setup
uv sync                         # Install dependencies
uv sync --all-extras            # Include voice, whoop, dev extras

# Development
uv run jarvis                   # CLI entrypoint
uv run jarvis serve             # Start API server (port 8000)
uv run jarvis status            # Check adapter connections
uv run jarvis chat              # Interactive AI chat
uv run jarvis ask "question"    # Single question to Clawd

# Testing & Quality
uv run pytest                   # Run all tests
uv run pytest tests/test_file.py::test_name  # Run single test
uv run mypy src/                # Type checking
uv run ruff check src/          # Lint
uv run ruff format src/         # Format
```

## Architecture

```
User Input (WhatsApp/CLI/API)
         ↓
    Clawd AI Agent (Pydantic AI + OpenRouter/Bedrock)
         ↓
    Tools → Aggregators → Adapters → External APIs
```

### Adapter Pattern

All data source connectors inherit from `BaseAdapter` in `src/jarvis/adapters/base.py`:

```python
class BaseAdapter(ABC):
    async def connect() -> bool
    async def disconnect() -> None
    async def health_check() -> bool
    async def fetch(start_date, end_date, **kwargs) -> dict
```

Adapters are async context managers. Use `async with Adapter() as adapter:` pattern.

### Aggregators

Combine data from multiple adapters with priority-based merging:
- `HealthAggregator`: Merges Whoop (sleep/recovery) + Garmin (steps/activities)
- `CalendarAggregator`: Merges Google + Outlook events
- `DailyAggregator`: Combines health + calendar + tasks for briefings

### Clawd AI Agent

Located in `src/jarvis/clawd/`. Uses Pydantic AI with tools defined in `tools.py`:
- `get_tasks()` - From Obsidian Tasks.md
- `search_notes(query)` - Full-text Obsidian search
- `get_health_summary()` - Merged Whoop + Garmin data
- `get_calendar_events()` - Today's events

Agent initialization is lazy (via `get_agent()`) to avoid import-time API calls.

## Configuration

All settings via Pydantic Settings in `src/jarvis/config/settings.py`. Environment variables loaded from `.env`:

- `GARMIN_EMAIL`, `GARMIN_PASSWORD` - Garmin Connect
- `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET` - Whoop OAuth
- `GOOGLE_CREDENTIALS_FILE`, `GOOGLE_TOKEN_FILE` - Google Calendar
- `OBSIDIAN_VAULT_PATH` - Path to Obsidian vault
- `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN` - Home Assistant
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` - AI model config
- `AWS_BEARER_TOKEN_BEDROCK`, `AWS_REGION` - Bedrock (for OpenClaw)

## Key Integration Points

### Obsidian
- Daily notes at `OBSIDIAN_VAULT_PATH/Notes/YYYY-MM-DD.md`
- Tasks: `- [ ]` (incomplete) / `- [x]` (complete)
- Journals at `OBSIDIAN_VAULT_PATH/YYYY/Mon/Mon D.md`

### Whoop/Garmin
- Whoop: OAuth with auto-refresh timer (systemd)
- Garmin: Direct login credentials
- Health data merging prioritizes Whoop for sleep/recovery, Garmin for steps

### WhatsApp (OpenClaw)
- Gateway runs as systemd user service on Pi
- Skills in `~/.openclaw/skills/jarvis/SKILL.md`
- Workspace config in `~/jarvis-workspace/TOOLS.md` and `SOUL.md`
- Morning briefing via cron: `openclaw cron list`

## Deployment

**Pi 5** (10.0.0.7): Brain - JARVIS API, OpenClaw, Obsidian
**Pi 4** (10.0.0.223): Data - Home Assistant

Systemd services:
- `jarvis-api.service` - Web API
- `whoop-refresh.timer` - Token refresh every 30 min
- `openclaw-gateway.service` (user) - WhatsApp gateway

Deploy: `rsync -avz --exclude '.venv' . pi@10.0.0.7:~/life_os/`

## Code Patterns

- **Async**: All I/O operations use async/await
- **Logging**: `structlog` with context binding
- **Models**: Pydantic for validation, SQLModel for database
- **Errors**: Custom exception hierarchy in `adapters/base.py`
