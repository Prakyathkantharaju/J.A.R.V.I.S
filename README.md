# JARVIS - Personal AI Assistant

JARVIS (Just A Rather Very Intelligent System) is a modular personal assistant that aggregates data from multiple life sources and runs on Raspberry Pi hardware.

![JARVIS Dashboard](docs/images/dashboard.png)

## Overview

JARVIS connects to your health trackers, calendars, notes, and smart home to provide unified access to your personal data. It runs as a distributed system across two Raspberry Pis.

## Architecture

```
Mac/Desktop                    Pi 5 (Brain)                 Pi 4 (Data)
+-----------+                 +-------------+              +---------------+
| Claude    | <-- SSH/CLI --> | JARVIS CLI  |              | Home Assistant|
| Code      |                 | Clawdbot    |              | Redis (future)|
+-----------+                 | (WhatsApp)  |              +---------------+
                              +-------------+
      Phone                         |                            |
+-----------+                       +------- Network ------------+
| WhatsApp  | <-- Clawdbot -------->|
+-----------+                       |
                    +---------------+---------------+
                    |               |               |
                 Garmin          Whoop          Google
                 Connect          API           Calendar
```

## Hardware

| Device | IP | Role |
|--------|-----|------|
| Pi 5 | 10.0.0.7 | Brain - runs JARVIS CLI, adapters, future voice |
| Pi 4 | 10.0.0.223 | Data - runs Home Assistant |

## Code Structure

```
life_os/
├── src/jarvis/
│   ├── adapters/           # Data source connectors
│   │   ├── base.py         # Abstract adapter interface
│   │   ├── garmin.py       # Garmin Connect (steps, HR, activities)
│   │   ├── whoop.py        # Whoop API (sleep, recovery, strain)
│   │   ├── google_calendar.py  # Google Calendar
│   │   ├── outlook.py      # Microsoft Graph / Outlook
│   │   ├── obsidian.py     # Local vault parser
│   │   └── home_assistant.py   # Smart home control
│   │
│   ├── aggregators/        # Combine data from multiple sources
│   │   ├── health.py       # Whoop + Garmin health metrics
│   │   ├── calendar.py     # Google + Outlook merged view
│   │   └── daily.py        # Daily briefing generator
│   │
│   ├── config/
│   │   └── settings.py     # Pydantic settings from .env
│   │
│   ├── autonomous/
│   │   └── scheduler.py    # APScheduler for automated routines
│   │
│   ├── voice/              # Future: voice interaction
│   │   └── pipeline.py     # Wake word + STT + TTS
│   │
│   ├── db/
│   │   └── models.py       # SQLModel database schemas
│   │
│   └── cli.py              # Typer CLI entry point
│
├── scripts/
│   ├── oauth_setup.py      # OAuth flows for Google/Whoop/etc
│   ├── whoop_auth.py       # Whoop OAuth helper
│   ├── whoop_exchange_code.py  # Exchange Whoop auth code
│   ├── setup_pi5.sh        # Pi 5 setup script
│   ├── setup_pi4.sh        # Pi 4 setup script
│   └── deploy.sh           # Rsync deployment
│
├── deploy/
│   ├── systemd/            # Service files for Pi
│   └── docker/             # Docker compose for HA
│
├── docs/
│   ├── SETUP_GUIDE.md      # Detailed adapter setup instructions
│   └── ORCHESTRATION.md    # How autonomous routines work
│
├── tests/
├── pyproject.toml
└── .env.example
```

## CLI Commands

```bash
jarvis status      # Check all adapter connections
jarvis health      # Show health data (Whoop + Garmin)
jarvis calendar    # Show merged calendar events
jarvis briefing    # Generate daily briefing
jarvis notes       # Search Obsidian vault
jarvis home        # Control Home Assistant devices
jarvis speak       # TTS via Home Assistant
jarvis sync        # Trigger data sync
jarvis serve       # Start web dashboard on port 8000
jarvis chat        # Chat with Clawd AI assistant
jarvis ask "..."   # Quick question to Clawd
```

## Clawd AI Assistant

Clawd is a personal AI assistant powered by Claude (Anthropic). It has access to:

- **Obsidian vault**: Tasks, notes, saved articles, food logs
- **Health data**: Sleep, recovery, strain from Whoop/Garmin
- **Calendar**: Events from Google Calendar

```bash
# Interactive chat
jarvis chat

# Single question
jarvis ask "What are my tasks for today?"
jarvis ask "How did I sleep last night?"
```

## WhatsApp Integration (Clawdbot)

JARVIS integrates with WhatsApp via [Clawdbot](https://clawd.bot), allowing you to interact with your personal data from your phone.

### Features

- **Morning Briefing**: Automatic daily briefing at 6 AM Eastern with tasks, health data, and calendar
- **Task Queries**: "What are my tasks?" reads from your Obsidian daily notes
- **Health Queries**: "How did I sleep?" fetches Whoop/Garmin data
- **Journaling**: Say "let me journal" to start a guided journaling session that saves to your Obsidian vault

### Journaling via WhatsApp

1. Send "let me journal" or "journal time"
2. Clawd guides you through reflection with follow-up questions
3. Say "save" when done - entry saves to `YYYY/Mon/Mon D.md` in your vault

### Setup

```bash
# Install Clawdbot
sudo npm install -g clawdbot@latest

# Run setup
clawdbot onboard
clawdbot daemon install
systemctl --user enable --now clawdbot-gateway

# Add Anthropic API key
clawdbot models auth paste-token --provider anthropic

# Pair WhatsApp (scan QR code)
clawdbot channels login
```

See [SETUP_RECOVERY.md](docs/SETUP_RECOVERY.md) for complete setup instructions.

## Quick Start

```bash
# Clone and install
git clone <repo>
cd life_os
uv sync

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run locally
uv run jarvis status

# Deploy to Pi
rsync -avz --exclude '.venv' . pi@10.0.0.7:~/jarvis/
ssh pi@10.0.0.7 "cd ~/jarvis && source ~/.local/bin/env && uv run jarvis status"
```

## Documentation

- [Setup Guide](docs/SETUP_GUIDE.md) - Detailed instructions for each adapter
- [Orchestration](docs/ORCHESTRATION.md) - How autonomous routines work

## Current Adapter Status

| Adapter | Status | Notes |
|---------|--------|-------|
| Garmin | Working | Direct login |
| Whoop | Working | OAuth with auto-refresh every 30 min |
| Google Calendar | Working | OAuth required |
| Outlook | Not configured | Azure app registration needed |
| Obsidian | Working | Flatpak on Pi, auto-starts on boot |
| Home Assistant | Working | Running on Pi 4 |

## Systemd Services (Auto-start on boot)

```bash
# On Pi 5
sudo systemctl status jarvis-api          # Web dashboard & API
sudo systemctl status whoop-refresh       # Token refresh timer
systemctl --user status obsidian          # Obsidian app
systemctl --user status clawdbot-gateway  # WhatsApp gateway

# View logs
sudo journalctl -u jarvis-api -f
clawdbot logs --follow
```

## Dependencies

- Python 3.12+
- uv (package manager)
- Raspberry Pi OS 64-bit
