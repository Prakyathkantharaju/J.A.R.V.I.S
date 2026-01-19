# JARVIS Development Session Summary

## What Was Built

A personal AI assistant called JARVIS that integrates multiple data sources and runs on Raspberry Pi hardware.

## Infrastructure Setup

### Pi 5 (10.0.0.7) - Brain
- Installed uv package manager
- Deployed JARVIS Python code
- Installed all 74 Python dependencies
- Created systemd service files (jarvis-sync, jarvis-voice)
- Installed Obsidian via Flatpak for vault sync

### Pi 4 (10.0.0.223) - Data
- Installed Docker
- Deployed Home Assistant container
- Home Assistant accessible at http://10.0.0.223:8123

## Code Written

### Adapters (src/jarvis/adapters/)
- **base.py**: Abstract base class with connect/disconnect/fetch interface
- **garmin.py**: Garmin Connect integration using garminconnect library
- **whoop.py**: Whoop API integration using whoopy library
- **google_calendar.py**: Google Calendar via OAuth
- **outlook.py**: Microsoft Graph API for Outlook calendar
- **obsidian.py**: Local vault parser for notes and food logs
- **home_assistant.py**: Smart home control, TTS, location tracking

### Aggregators (src/jarvis/aggregators/)
- **health.py**: Combines Whoop + Garmin health data
- **calendar.py**: Merges Google + Outlook calendars with conflict detection
- **daily.py**: Generates morning briefings and evening reflections

### CLI (src/jarvis/cli.py)
Typer-based CLI with commands: status, health, calendar, briefing, notes, home, speak, sync

### Configuration (src/jarvis/config/settings.py)
Pydantic Settings loading from .env file with nested settings for each service

### Scripts
- **oauth_setup.py**: Multi-service OAuth setup wizard
- **whoop_auth.py**: Whoop-specific OAuth flow
- **whoop_exchange_code.py**: Exchange Whoop auth code for tokens
- **setup_pi5.sh / setup_pi4.sh**: Pi setup scripts
- **deploy.sh**: Rsync deployment script

## Bugs Fixed During Session

1. **Import path error**: Changed `from config.settings` to `from jarvis.config.settings`
2. **Settings not loading from .env**: Added `env_file=".env"` to all nested Pydantic Settings classes
3. **Home Assistant URL missing /api**: Fixed adapter to append `/api` to base URL
4. **Calendar crash on Outlook failure**: Made Outlook connection optional with try/catch
5. **Whoop OAuth method**: Changed from `authorize()` to `auth_flow()` for newer whoopy library

## Services Configured

| Service | Status | Method |
|---------|--------|--------|
| Garmin Connect | Connected | Email/password in .env |
| Whoop | Tokens obtained | OAuth flow via browser |
| Google Calendar | Connected | OAuth via oauth_setup.py |
| Home Assistant | Connected | Long-lived access token |
| Outlook | Not configured | Needs Azure app registration |
| Obsidian | Pending | Obsidian installed, needs Sync login |

## Files Created

```
45 files in initial commit:
- pyproject.toml
- .env.example
- .gitignore
- PROMPT.md, @fix_plan.md, @AGENT.md (Ralph files)
- src/jarvis/** (all Python modules)
- scripts/** (setup and OAuth scripts)
- deploy/** (systemd and docker configs)
- docs/** (SETUP_GUIDE.md, ORCHESTRATION.md)
- tests/conftest.py
```

## Commits Made

1. `9c2ce6f` - Initial commit: JARVIS personal AI assistant
2. `4cb237f` - Add comprehensive setup guide for all adapters
3. `61b2da7` - Add Whoop OAuth script
4. `3ccc5b4` - Fix calendar aggregator to handle missing adapters gracefully

## Next Steps

1. **Obsidian**: Connect monitor to Pi 5, run Obsidian, log into Obsidian Sync
2. **Outlook**: Register Azure app if Microsoft calendar needed
3. **Voice**: Configure Picovoice API key and pair Bluetooth speaker
4. **Systemd**: Enable jarvis-sync service for automated data fetching
5. **Testing**: Run full integration tests with all adapters

## Commands Reference

```bash
# Check status on Pi
ssh pi@10.0.0.7 "cd ~/jarvis && source ~/.local/bin/env && uv run jarvis status"

# Sync code to Pi
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' . pi@10.0.0.7:~/jarvis/

# Copy .env to Pi
scp .env pi@10.0.0.7:~/jarvis/.env
```
